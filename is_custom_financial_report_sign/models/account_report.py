# -*- coding: utf-8 -*-
from odoo import models, fields, api, _ # Añadido _ para traducciones
from odoo.tools.misc import get_lang
import babel.dates
import io
import logging

# --- IMPORTACIONES NECESARIAS ---
try:
    import openpyxl
    from openpyxl.styles import Font, Alignment
    from openpyxl.utils import get_column_letter # Importado para obtener letras de columna
except ImportError:
    openpyxl = None
# ------------------------------

_logger = logging.getLogger(__name__)

class AccountReport(models.Model):
    _inherit = 'account.report'

    show_sign_area = fields.Boolean(
        string="Show Sign Area",
        compute='_compute_show_sign_area'
    )

    def _compute_show_sign_area(self):
        # Asegúrate que 'account_reports.balance_sheet' sea el ID correcto
        financial_report = self.env.ref('account_reports.balance_sheet', raise_if_not_found=False)
        profit_and_loss = self.env.ref('account_reports.profit_and_loss', raise_if_not_found=False)

        for report in self:
            report_id = report.id
            is_financial_report = financial_report and report_id == financial_report.id
            is_profit_and_loss = profit_and_loss and report_id == profit_and_loss.id
            report.show_sign_area = is_financial_report or is_profit_and_loss

    def _format_date_es(self, date_obj):
        if not date_obj: return ''
        # Asegúrate de tener 'es_GT' instalado o usa 'es' como fallback
        lang_code = 'es_GT' if 'es_GT' in self.env['res.lang'].get_installed() else 'es'
        try:
            # Formato 'd de MMMM de y'
            formatted_date = babel.dates.format_date(date_obj, format='d MMMM y', locale=lang_code)
            parts = formatted_date.split(' ')
            if len(parts) == 3:
                 # Reconstruir con 'de'
                 return f"{parts[0]} de {parts[1]} de {parts[2]}"
            return formatted_date # Fallback al formato por defecto si no tiene 3 partes
        except Exception as e:
            _logger.error(f"Error formateando fecha {date_obj} con locale {lang_code}: {e}")
            # Fallback a formatos sin locale si babel falla
            try:
                # Intenta formato español con strftime (depende del locale del servidor)
                return date_obj.strftime('%d de %B de %Y')
            except:
                # Fallback final a formato numérico
                return date_obj.strftime('%d/%m/%Y')

    def _get_report_rendering_context(self, options):
        """Prepara el contexto solo con nuestras variables personalizadas."""
        # Intenta obtener el contexto base primero, si existe en la versión que usas
        render_context = {}
        if hasattr(super(), '_get_report_rendering_context'):
             render_context = super()._get_report_rendering_context(options)

        company = self.env.company
        report_name = self.name
        date_options = options.get('date', {})
        date_from_str = date_options.get('date_from')
        date_to_str = date_options.get('date_to')
        date_from = fields.Date.from_string(date_from_str) if date_from_str else None
        date_to = fields.Date.from_string(date_to_str) if date_to_str else None
        date_range_es = _("Periodo no especificado") # Usar _() para traducción
        if date_from and date_to: date_range_es = _("Del %s al %s") % (self._format_date_es(date_from), self._format_date_es(date_to))
        elif date_to: date_range_es = _("Al %s") % (self._format_date_es(date_to))
        currency_name = company.currency_id.full_name or _('Moneda no especificada')
        currency_es = _("(Expresado en %s)") % currency_name # Ahora sí usaremos esta variable

        # Actualizar el contexto base (o crearlo si no existe)
        render_context.update({
            'company_name': company.name or '',
            'company_vat': company.vat or '',
            'report_name': report_name or '',  # Nombre para nuestro encabezado
            'date_range_es': date_range_es,
            'currency_es': currency_es, # La mantenemos en el contexto y ahora la usaremos
            'report': self, # Asegurarse que 'report' esté
            'options': options, # Asegurarse que 'options' esté
            'data': self.env.company if self.show_sign_area else None,
            # Mantener otros valores que podrías necesitar del contexto base si existía
            'env': self.env,
            'report_company_name': company.display_name,
            'report_title': self.name,
        })
        return render_context

    def get_html(self, options, *args, **kwargs):
        local_context = self._get_report_rendering_context(options)
        original_additional_context = kwargs.get('additional_context', {})
        merged_additional_context = {**original_additional_context, **local_context}
        kwargs['additional_context'] = merged_additional_context
        html = super(AccountReport, self.with_context(discard_logo_check=True)).get_html(options, *args, **kwargs)
        if isinstance(html, bytes): html = html.decode('utf-8')
        return html

    def get_report_informations(self, options):
        info = super().get_report_informations(options)
        self.sudo()._compute_show_sign_area()
        info['show_sign_area'] = self.show_sign_area
        return info

    def export_to_xlsx(self, options, response=None):
        _logger.info(f"--- EJECUTANDO export_to_xlsx PARA REPORTE: {self.name} ---")
        original_export_data = super(AccountReport, self.with_context(discard_logo_check=True)).export_to_xlsx(options, response)
        original_output_bytes = original_export_data['file_content']
        self.sudo()._compute_show_sign_area()
        _logger.info(f"--- Valor de show_sign_area: {self.show_sign_area} ---")

        if not self.show_sign_area:
            _logger.info("Reporte no configurado para firmas, devolviendo XLSX estándar.")
            return original_export_data
        if not openpyxl:
            _logger.warning("La librería 'openpyxl' no está instalada. Devolviendo XLSX estándar.")
            return original_export_data

        _logger.info(f"--- MODIFICANDO XLSX CON ENCABEZADO Y FIRMAS (reporte: {self.name}) ---")
        original_output_stream = io.BytesIO(original_output_bytes)
        try:
            workbook = openpyxl.load_workbook(original_output_stream)
            try: sheet = workbook.active
            except Exception: sheet = workbook.worksheets[0]
            company = self.env.company
            bold_font = Font(name='Arial', size=12, bold=True)
            normal_font = Font(name='Arial', size=11)
            center_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
            left_align = Alignment(horizontal='left', vertical='center', wrap_text=True)
            sign_center_align = Alignment(horizontal='center', vertical='bottom')

            # --- CORRECCIÓN MEJORADA v2: Agregar Encabezado Dinámico CON AJUSTES ---
            render_context = self._get_report_rendering_context(options)
            _logger.info(f"--- Variables de contexto para encabezado ---")
            _logger.info(f"company_name: {render_context.get('company_name')}")
            _logger.info(f"company_vat: {render_context.get('company_vat')}")
            _logger.info(f"report_name: {render_context.get('report_name')}")
            _logger.info(f"date_range_es: {render_context.get('date_range_es')}")
            # AHORA INCLUIREMOS currency_es
            _logger.info(f"currency_es: {render_context.get('currency_es')}")

            header_lines = []
            if render_context.get('company_name'): header_lines.append(str(render_context.get('company_name', '')).upper())
            if render_context.get('company_vat'): header_lines.append(f"VAT: {render_context.get('company_vat', '')}")
            if render_context.get('report_name'): header_lines.append(str(render_context.get('report_name', '')).upper())
            if render_context.get('date_range_es'): header_lines.append(str(render_context.get('date_range_es', '')))
            # --- Añadir currency_es al final ---
            if render_context.get('currency_es'): header_lines.append(str(render_context.get('currency_es', '')))
            # --- Fin añadir currency_es ---

            header_text = "\n".join(filter(lambda x: x is not None, header_lines)) # Usar filter para permitir "" pero no None
            _logger.info(f"--- Texto final del encabezado para Excel: ---\n{header_text}")

            if header_text:
                sheet.insert_rows(1)
                num_lines_in_header = header_text.count('\n') + 1
                new_height = max(20, num_lines_in_header * 15)
                if 1 in sheet.row_dimensions: sheet.row_dimensions[1].height = new_height
                else: sheet.row_dimensions[1] = openpyxl.worksheet.dimensions.RowDimension(sheet, index=1, ht=new_height)
                _logger.info(f"Ajustando altura de fila 1 a: {new_height}")

                max_col = sheet.max_column if sheet.max_column >= 1 else 1
                max_col_letter = get_column_letter(max_col)
                merge_range = f'A1:{max_col_letter}1'
                try: sheet.merge_cells(merge_range)
                except Exception as merge_err:
                    _logger.error(f"Error al combinar celdas para encabezado '{merge_range}': {merge_err}. Intentando con A1.")
                    merge_range = 'A1'

                cell = sheet['A1']
                cell.value = header_text
                cell.font = bold_font
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            # --- FIN CORRECCIÓN ENCABEZADO ---

                # --- INICIO: Eliminar filas originales no deseadas ---
                rows_to_delete = []
                # Revisar las primeras filas DESPUÉS de nuestro encabezado (que está en la fila 1)
                # El contenido original ahora empieza en la fila 2
                max_rows_to_check = 5  # Revisar las primeras 5 filas del contenido original
                for row_idx in range(2, min(sheet.max_row + 1, 2 + max_rows_to_check)):
                    # Obtener el valor de la primera celda (A) en la fila actual
                    cell_value = sheet.cell(row=row_idx, column=1).value
                    if isinstance(cell_value, str):
                        # Comprobar si contiene el texto de fecha o la palabra "Balance"
                        # Usamos .strip() para quitar espacios y lower() para ignorar mayúsculas/minúsculas
                        cell_text = cell_value.strip().lower()
                        # Puedes ajustar estas condiciones si el texto varía
                        if "partir de" in cell_text or "balance" == cell_text:
                            _logger.info(f"Marcando fila {row_idx} para eliminar (contenido: '{cell_value}')")
                            rows_to_delete.append(row_idx)

                # Eliminar las filas marcadas, empezando desde la más alta para no afectar los índices inferiores
                for row_idx in sorted(rows_to_delete, reverse=True):
                    _logger.info(f"Eliminando fila {row_idx}")
                    sheet.delete_rows(row_idx, amount=1)
                # --- FIN: Eliminar filas originales no deseadas ---


            # --- Certificación y Firmas (sin cambios, ya corregido antes) ---
            # ... (el código de certificación y firmas vertical permanece igual) ...
            current_row = sheet.max_row + 3
            max_col = sheet.max_column if sheet.max_column >= 1 else 1
            max_col_letter = get_column_letter(max_col)
            if company.certification_text:
                merge_range_cert = f'A{current_row}:{max_col_letter}{current_row + 1}' if max_col >= 1 else f'A{current_row}'
                try: sheet.merge_cells(merge_range_cert)
                except Exception as merge_err: _logger.error(f"Error al combinar celdas para certificación '{merge_range_cert}': {merge_err}.")
                cell = sheet[f'A{current_row}']
                cell.value = company.certification_text
                cell.font = normal_font; cell.alignment = left_align
                if current_row in sheet.row_dimensions: sheet.row_dimensions[current_row].height = max(15, len(company.certification_text.split('\n')) * 15)
                current_row += 3
            signatures = []
            if company.name_1 and company.position_1: signatures.append((company.name_1, company.position_1))
            if company.name_2 and company.position_2: signatures.append((company.name_2, company.position_2))
            if company.name_3 and company.position_3: signatures.append((company.name_3, company.position_3))
            if signatures:
                col_start = 1; col_end = min(2, max_col); start_letter = get_column_letter(col_start); end_letter = get_column_letter(col_end); can_merge = col_end > col_start
                for i, (name, title) in enumerate(signatures):
                    if i > 0: current_row += 2
                    sign_line_row = current_row; sign_name_row = current_row + 1; sign_title_row = current_row + 2
                    try:
                        merge_range_line = f'{start_letter}{sign_line_row}:{end_letter}{sign_line_row}' if can_merge else f'{start_letter}{sign_line_row}'
                        if can_merge: sheet.merge_cells(merge_range_line)
                        cell_line = sheet.cell(row=sign_line_row, column=col_start); cell_line.value = "___________________________"; cell_line.alignment = sign_center_align; cell_line.font = normal_font
                        if sign_line_row in sheet.row_dimensions: sheet.row_dimensions[sign_line_row].height = 15
                        merge_range_name = f'{start_letter}{sign_name_row}:{end_letter}{sign_name_row}' if can_merge else f'{start_letter}{sign_name_row}'
                        if can_merge: sheet.merge_cells(merge_range_name)
                        cell_name = sheet.cell(row=sign_name_row, column=col_start); cell_name.value = name; cell_name.alignment = sign_center_align; cell_name.font = bold_font
                        if sign_name_row in sheet.row_dimensions: sheet.row_dimensions[sign_name_row].height = 15
                        merge_range_title = f'{start_letter}{sign_title_row}:{end_letter}{sign_title_row}' if can_merge else f'{start_letter}{sign_title_row}'
                        if can_merge: sheet.merge_cells(merge_range_title)
                        cell_title = sheet.cell(row=sign_title_row, column=col_start); cell_title.value = title; cell_title.alignment = sign_center_align; cell_title.font = normal_font
                        if sign_title_row in sheet.row_dimensions: sheet.row_dimensions[sign_title_row].height = 15
                        current_row = sign_title_row + 1
                    except Exception as merge_err:
                        _logger.error(f"Error al procesar/combinar celdas para la firma {i+1} (vertical): {merge_err}")
                        current_row = sign_title_row + 1

            # 6. Guardar los bytes modificados
            new_output = io.BytesIO()
            workbook.save(new_output)
            new_output.seek(0)
            modified_bytes = new_output.read()

            # 7. DEVOLVER EL DICCIONARIO CON LOS BYTES MODIFICADOS
            original_export_data['file_content'] = modified_bytes
            return original_export_data

        except Exception as e:
            _logger.error(f"Error CRÍTICO al modificar el archivo XLSX (reporte: {self.name}): {e}", exc_info=True)
            original_export_data['file_content'] = original_output_bytes
            return original_export_data