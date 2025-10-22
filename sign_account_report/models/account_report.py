from odoo import models, _
import base64
import io
import re
import logging
from datetime import datetime
import markupsafe

_logger = logging.getLogger(__name__)

class AccountReportCustom(models.Model):
    _inherit = 'account.report'

    def _inject_report_into_xlsx_sheet(self, options, workbook, sheet):
        def write_with_colspan(sheet, x, y, value, colspan, style):
            if colspan == 1:
                sheet.write(y, x, value, style)
            else:
                sheet.merge_range(y, x, y, x + colspan - 1, value, style)

        title_format = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
        default_format_props = {'font_name': 'Arial', 'font_color': '#666666', 'font_size': 12, 'num_format': '#,##0.00'}
        text_format_props = {'font_name': 'Arial', 'font_color': '#666666', 'font_size': 12}
        date_format_props = {'font_name': 'Arial', 'font_color': '#666666', 'font_size': 12, 'num_format': 'yyyy-mm-dd'}
        workbook_formats = {
            0: {
                'default': workbook.add_format({**default_format_props, 'bold': True, 'font_size': 13, 'bottom': 6}),
                'text': workbook.add_format({**text_format_props, 'bold': True, 'font_size': 13, 'bottom': 6}),
                'date': workbook.add_format({**date_format_props, 'bold': True, 'font_size': 13, 'bottom': 6}),
                'total': workbook.add_format({**default_format_props, 'bold': True, 'font_size': 13, 'bottom': 6}),
            },
            1: {
                'default': workbook.add_format({**default_format_props, 'bold': True, 'font_size': 13, 'bottom': 1}),
                'text': workbook.add_format({**text_format_props, 'bold': True, 'font_size': 13, 'bottom': 1}),
                'date': workbook.add_format({**date_format_props, 'bold': True, 'font_size': 13, 'bottom': 1}),
                'total': workbook.add_format({**default_format_props, 'bold': True, 'font_size': 13, 'bottom': 1}),
                'default_indent': workbook.add_format({**default_format_props, 'bold': True, 'font_size': 13, 'bottom': 1, 'indent': 1}),
                'date_indent': workbook.add_format({**date_format_props, 'bold': True, 'font_size': 13, 'bottom': 1, 'indent': 1}),
            },
            2: {
                'default': workbook.add_format({**default_format_props, 'bold': True}),
                'text': workbook.add_format({**text_format_props, 'bold': True}),
                'date': workbook.add_format({**date_format_props, 'bold': True}),
                'initial': workbook.add_format(default_format_props),
                'total': workbook.add_format({**default_format_props, 'bold': True}),
                'default_indent': workbook.add_format({**default_format_props, 'bold': True, 'indent': 2}),
                'date_indent': workbook.add_format({**date_format_props, 'bold': True, 'indent': 2}),
                'initial_indent': workbook.add_format({**default_format_props, 'indent': 2}),
                'total_indent': workbook.add_format({**default_format_props, 'bold': True, 'indent': 1}),
            },
            'default': {
                'default': workbook.add_format(default_format_props),
                'text': workbook.add_format(text_format_props),
                'date': workbook.add_format(date_format_props),
                'total': workbook.add_format(default_format_props),
                'default_indent': workbook.add_format({**default_format_props, 'indent': 2}),
                'date_indent': workbook.add_format({**date_format_props, 'indent': 2}),
                'total_indent': workbook.add_format({**default_format_props, 'indent': 2}),
            },
        }

        def get_format(content_type='default', level='default'):
            if isinstance(level, int) and level not in workbook_formats:
                workbook_formats[level] = {
                    **workbook_formats['default'],
                    'default_indent': workbook.add_format({**default_format_props, 'indent': level}),
                    'date_indent': workbook.add_format({**date_format_props, 'indent': level}),
                    'total_indent': workbook.add_format({**default_format_props, 'bold': True, 'indent': level - 1}),
                }

            level_formats = workbook_formats[level]
            if '_indent' in content_type and not level_formats.get(content_type):
                return level_formats.get('default_indent', level_formats.get(content_type.removesuffix('_indent'), level_formats['default']))
            return level_formats.get(content_type, level_formats['default'])

        print_mode_self = self.with_context(no_format=True)
        lines = self._filter_out_folded_children(print_mode_self._get_lines(options))

        # For reports with lines generated for accounts, the account name and codes are shown in a single column.
        # To help user post-process the report if they need, we should in such a case split the account name and code in two columns.
        account_lines_split_names = {}
        for line in lines:
            line_model = self._get_model_info_from_id(line['id'])[0]
            if line_model == 'account.account':
                # Reuse the _split_code_name to split the name and code in two values.
                account_lines_split_names[line['id']] = self.env['account.account']._split_code_name(line['name'])

        # Set the (Account) Name column width to 50.
        # If we have account lines and split the name and code in two columns, we will also set the code column.
        if len(account_lines_split_names) > 0:
            sheet.set_column(0, 0, 11)
            sheet.set_column(1, 1, 50)
        else:
            sheet.set_column(0, 0, 50)

        original_x_offset = 1 if len(account_lines_split_names) > 0 else 0
        ################################################ INSERTAMOS ENCABEZADO PERZONALIZADO ········································
        # === ENCABEZADO PERSONALIZADO ===
        report_id = options.get('report_id')
        signature = self.env['custom.report.signature'].sudo().search([
            ('report_id', '=', self.id),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        y_offset = 0

        if signature and report_id == 20: #TODO HACER DINAMICO DESDE LA CONFIGURACION DE LA COMPANIA
            y_offset = 5
            journal_id = options.get('bank_reconciliation_report_journal_id')
            bold_center_format = workbook.add_format(
                { 'bold': True, 'font_size': 12, 'align': 'center'})
            small_center_format = workbook.add_format({'font_name': 'Arial', 'font_size': 10, 'align': 'center'})
            journal_account_name = ''
            if journal_id:
                journal = self.env['account.journal'].browse(journal_id)
                journal_account_name = journal.default_account_id.code + f' {journal.default_account_id.name}'
            company_name = f"LIBRO DE BANCO CONCILIADO: {self.env.company.name}"
            report_name = f" CUENTA: {journal_account_name}" or ''
            date_from = options.get('date', {}).get('date_from') or ''
            date_to = options.get('date', {}).get('date_to') or ''
            simple_date = options.get('date', {}).get('string') or ''
            date_from_fmt = ''
            date_to_fmt = ''
            if date_from:
                date_from_fmt = datetime.strptime(date_from, '%Y-%m-%d').strftime('%d/%m/%Y')
            if date_to:
                date_to_fmt = datetime.strptime(date_to, '%Y-%m-%d').strftime('%d/%m/%Y')
            try:
                image_data = base64.b64decode(re.sub("^data:image/[^;]+;base64,", "", signature.imagen.strip()))
                image_stream = io.BytesIO(image_data)
                sheet.insert_image(0, 3, "logo.png", {
                    'image_data': image_stream,
                    'x_scale': 0.6,
                    'y_scale': 0.6,
                    'x_offset': 2,
                    'y_offset': 2,
                })
            except Exception as e:
                _logger.warning("No se pudo insertar la imagen del encabezado: %s", e)

            # Escribir encabezado en columnas combinadas
            max_col = len(options.get('columns', [])) + (2 if options.get('show_growth_comparison') else 1)

            def merge_center(row, text, fmt):
                sheet.merge_range(row, 0, row, 2, text, fmt)

            merge_center(0, company_name, bold_center_format)
            merge_center(1, report_name, bold_center_format)
            #merge_center(2, f"Fecha: Del {date_from_fmt} Al {date_to_fmt}", bold_center_format)
            merge_center(2, f"{simple_date}", bold_center_format)
        ############################## FIN DE ENCABEZADOS  ······················"·············



        # 1 and not 0 to leave space for the line name. original_x_offset allows making place for the code column if needed.
        x_offset = original_x_offset + 1

        # Add headers.
        # For this, iterate in the same way as done in main_table_header template
        column_headers_render_data = self._get_column_headers_render_data(options)
        for header_level_index, header_level in enumerate(options['column_headers']):
            if not signature: # SI TIENE SIGNATURE ES PARA REPORTE Y OMITIMOS LA COLUMNA POR DEFECTO DE "AL {FECHA}"
                for header_to_render in header_level * column_headers_render_data['level_repetitions'][header_level_index]:
                    colspan = header_to_render.get('colspan', column_headers_render_data['level_colspan'][header_level_index])
                    write_with_colspan(sheet, x_offset, y_offset, header_to_render.get('name', ''), colspan, title_format)
                    x_offset += colspan
            if options['show_growth_comparison']:
                write_with_colspan(sheet, x_offset, y_offset, '%', 1, title_format)
            y_offset += 1
            x_offset = original_x_offset + 1

        for subheader in column_headers_render_data['custom_subheaders']:
            colspan = subheader.get('colspan', 1)
            write_with_colspan(sheet, x_offset, y_offset, subheader.get('name', ''), colspan, title_format)
            x_offset += colspan
        y_offset += 1
        x_offset = original_x_offset + 1

        if account_lines_split_names:
            # If we have a separate account code column, add a title for it
            sheet.write(y_offset, x_offset - 2, _("Code"), title_format)
            sheet.write(y_offset, x_offset - 1, _("Account Name"), title_format)
        sheet.set_column(x_offset, x_offset + len(options['columns']), 10)

        for column in options['columns']:
            colspan = column.get('colspan', 1)
            write_with_colspan(sheet, x_offset, y_offset, column.get('name', ''), colspan, title_format)
            x_offset += colspan
        y_offset += 1

        if options.get('order_column'):
            lines = self.sort_lines(lines, options)

        # Disable bold styling for the max level.
        max_level = max(line.get('level', -1) for line in lines) if lines else -1
        if max_level in {0, 1, 2}:
            # Total lines are supposed to be a level above, so we don't touch them.
            for wb_format in (s for s in workbook_formats[max_level] if 'total' not in s):
                workbook_formats[max_level][wb_format].set_bold(False)

        # Add lines.
        for y, line in enumerate(lines):
            level = line.get('level')
            if level == 0:
                y_offset += 1
            elif not level:
                level = 'default'

            line_id = self._parse_line_id(line.get('id'))
            is_initial_line = line_id[-1][0] == 'initial' if line_id else False
            is_total_line = line_id[-1][0] == 'total' if line_id else False

            # Write the first column(s), with a specific style to manage the indentation.
            cell_type, cell_value = self._get_cell_type_value(line)
            account_code_cell_format = get_format('text', level)

            if cell_type == 'date':
                cell_format = get_format('date_indent', level)
            elif is_initial_line:
                cell_format = get_format('initial_indent', level)
            elif is_total_line:
                cell_format = get_format('total_indent', level)
            else:
                cell_format = get_format('default_indent', level)

            x_offset = original_x_offset + 1
            if lines[y]['id'] in account_lines_split_names:
                # Write the Account Code and Name columns.
                code, name = account_lines_split_names[lines[y]['id']]
                # Don't indent the account code and don't format is as a monetary value either.
                sheet.write(y + y_offset, 0, code, account_code_cell_format)
                sheet.write(y + y_offset, 1, name, cell_format)
            else:
                write_method = sheet.write_datetime if cell_type == 'date' else sheet.write
                write_method(y + y_offset, original_x_offset, cell_value, cell_format)

                if 'parent_id' in line and line['parent_id'] in account_lines_split_names:
                    sheet.write(y + y_offset, 1 + original_x_offset, account_lines_split_names[line['parent_id']][0], account_code_cell_format)
                elif account_lines_split_names:
                    sheet.write(y + y_offset, 1 + original_x_offset, "", account_code_cell_format)

            # Write all the remaining cells.
            columns = line['columns']
            if options['show_growth_comparison'] and 'growth_comparison_data' in line:
                columns += [line['growth_comparison_data']]
            for x, column in enumerate(columns, start=x_offset):
                cell_type, cell_value = self._get_cell_type_value(column)

                if cell_type == 'date':
                    cell_format = get_format('date', level)
                elif is_initial_line:
                    cell_format = get_format('initial', level)
                elif is_total_line:
                    cell_format = get_format('total', level)
                else:
                    cell_format = get_format('default', level)

                write_method = sheet.write_datetime if cell_type == 'date' else sheet.write
                write_method(y + y_offset, x + line.get('colspan', 1) - 1, cell_value, cell_format)

        ############### INSERTAMOS FIRMAS  ################################
        if signature:
            ignature_format = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'top': 1,  # Borde superior

            })
            label_format = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'font_size': 10,
            })
            row = sheet.dim_rowmax + 6
            if signature.firma1:
                sheet.write(row-1, 1, f"Hecho Por::",label_format)
                sheet.merge_range(row, 2,row,3, f"{signature.firma1}",ignature_format)
                sheet.merge_range(row+1, 2, row+1,3, "Contabilidad",label_format)

            if signature.firma2:
                sheet.write(row-1, 5, f"Revisado Por:", label_format)
                sheet.merge_range(row, 6,row,7, f"{signature.firma2}",ignature_format)
                sheet.merge_range(row+1, 6,row+1,7, "Contabilidad",label_format)
#                 VO BO
                sheet.merge_range(row+6, 3, row+6, 5, f"Vo. Bo.", ignature_format)


        # SOBREESCRIBMOS DATOS PARA PDF

    def _get_pdf_export_html(self, options, lines, additional_context=None, template=None):
        print("jsldj _get_pdf_export_html", options)

        report_info = self.get_report_information(options)

        custom_print_templates = report_info['custom_display'].get('pdf_export', {})
        template = custom_print_templates.get('pdf_export_main', 'account_reports.pdf_export_main')


        ##################### INSETAMOS CAMBIOS ########
        report_id = options.get('report_id', False)
        journal_id = options.get('bank_reconciliation_report_journal_id')
        journal_account_name = ''
        if journal_id:
            journal = self.env['account.journal'].browse(journal_id)
            journal_account_name = journal.default_account_id.code + f' {journal.default_account_id.name}'
        company_name = f"LIBRO DE BANCO CONCILIADO: {self.env.company.name}"
        report_name = f" CUENTA: {journal_account_name}" or ''
        signature = self.env['custom.report.signature'].sudo().search([
            ('report_id', '=', report_id),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        logo_data_url = ''
        if signature and signature.imagen:
            try:
                image_base64 = re.sub("^data:image/[^;]+;base64,", "", signature.imagen.strip())
                logo_data_url = 'data:image/png;base64,%s' % image_base64
            except Exception:
                pass  #

        render_values = {
            'firma1': signature.firma1 if signature else '',
            'firma2': signature.firma2 if signature else '',
            'logo':logo_data_url,
            'company_name':company_name,
            'report_name':report_name,
            'report': self,
            'report_title': self.name,
            'options': options,
            'table_start': markupsafe.Markup('<tbody>'),
            'table_end': markupsafe.Markup('''
                   </tbody></table>
                   <div style="page-break-after: always"></div>
                   <table class="o_table table-hover">
               '''),
            'column_headers_render_data': self._get_column_headers_render_data(options),
            'custom_templates': custom_print_templates,
        }
        if additional_context:
            render_values.update(additional_context)

        if options.get('order_column'):
            lines = self.sort_lines(lines, options)

        lines = self._format_lines_for_display(lines, options)

        render_values['lines'] = lines

        # Manage footnotes.
        footnotes_to_render = []
        number = 0
        for line in lines:
            footnote_data = report_info['footnotes'].get(str(line.get('id')))
            if footnote_data:
                number += 1
                line['footnote'] = str(number)
                footnotes_to_render.append({'id': footnote_data['id'], 'number': number, 'text': footnote_data['text']})

        render_values['footnotes'] = footnotes_to_render

        options['css_custom_class'] = report_info['custom_display'].get('css_custom_class', '')

        # Render.
        return self.env['ir.qweb']._render(template, render_values)

