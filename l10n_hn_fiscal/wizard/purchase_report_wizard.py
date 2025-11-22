# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools.misc import format_date
import io
import base64
import xlsxwriter


class PurchaseReportWizard(models.TransientModel):
    _name = 'purchase_report_wizard'
    _description = 'Wizard para Generar Reporte de Compras'

    date_from = fields.Date(string='Fecha Desde', required=True, default=lambda self: datetime.now().replace(day=1).date())
    date_to = fields.Date(string='Fecha Hasta', required=True, default=lambda self: (datetime.now().replace(day=1) + relativedelta(months=1) - relativedelta(days=1)).date())
    config_id = fields.Many2one(
        'sales_report_configuration',
        string='Configuración',
        required=True,
        domain="[('report_name', '=', 'purchase_report')]",
        readonly=True
    )
    folio_inicial = fields.Integer(string='No. de Folio Inicial', required=True, default=1)
    has_taxes = fields.Boolean(string='Tiene Impuestos', compute='_compute_has_taxes', store=False)
    has_journals = fields.Boolean(string='Tiene Diarios', compute='_compute_has_journals', store=False)
    taxes_display = fields.Char(string='Impuestos', compute='_compute_taxes_display', store=False)
    journals_display = fields.Char(string='Diarios', compute='_compute_journals_display', store=False)
    name = fields.Char(string='Nombre archivo', size=32)
    archivo = fields.Binary(string='Archivo')

    @api.depends('config_id', 'config_id.report_taxes')
    def _compute_has_taxes(self):
        for rec in self:
            rec.has_taxes = bool(rec.config_id and rec.config_id.report_taxes and len(rec.config_id.report_taxes) > 0)

    @api.depends('config_id', 'config_id.journal_ids')
    def _compute_has_journals(self):
        for rec in self:
            rec.has_journals = bool(rec.config_id and rec.config_id.journal_ids and len(rec.config_id.journal_ids) > 0)

    @api.depends('config_id', 'config_id.report_taxes')
    def _compute_taxes_display(self):
        for rec in self:
            if rec.config_id and rec.config_id.report_taxes:
                rec.taxes_display = ', '.join(rec.config_id.report_taxes.mapped('name'))
            else:
                rec.taxes_display = ''

    @api.depends('config_id', 'config_id.journal_ids')
    def _compute_journals_display(self):
        for rec in self:
            if rec.config_id and rec.config_id.journal_ids:
                rec.journals_display = ', '.join(rec.config_id.journal_ids.mapped('name'))
            else:
                rec.journals_display = ''

    @api.model
    def default_get(self, fields_list):
        """Busca automáticamente la configuración de purchase_report"""
        res = super().default_get(fields_list)
        # Buscar la configuración de purchase_report
        config = self.env['sales_report_configuration'].search([
            ('report_name', '=', 'purchase_report')
        ], limit=1)
        if config:
            res['config_id'] = config.id
            # Forzar el cálculo de los campos computed
            if 'has_taxes' in fields_list or 'taxes_display' in fields_list:
                res['has_taxes'] = bool(config.report_taxes and len(config.report_taxes) > 0)
                res['taxes_display'] = ', '.join(config.report_taxes.mapped('name')) if config.report_taxes else ''
            if 'has_journals' in fields_list or 'journals_display' in fields_list:
                res['has_journals'] = bool(config.journal_ids and len(config.journal_ids) > 0)
                res['journals_display'] = ', '.join(config.journal_ids.mapped('name')) if config.journal_ids else ''
        return res

    def action_generate_report(self):
        """Genera el reporte PDF"""
        self.ensure_one()
        
        # Preparar los datos para el reporte
        data = {
            'ids': [self.id],
            'model': 'purchase_report_wizard',
            'form': self.read()[0]
        }
        
        # Generar el reporte pasando los datos del wizard
        return self.env.ref('l10n_hn_fiscal.action_report_purchase_book').report_action(self, data=data)

    def _hex_to_rgb(self, hex_color):
        """Convierte un color hex a RGB"""
        if not hex_color:
            return (211, 211, 211)  # Gris claro por defecto
        
        if isinstance(hex_color, str):
            hex_color = hex_color.strip()
            if not hex_color.startswith('#'):
                hex_color = '#' + hex_color
        
        try:
            hex_color = str(hex_color).lstrip('#')
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                return (r, g, b)
        except (ValueError, AttributeError):
            pass
        
        return (211, 211, 211)  # Gris claro por defecto

    def action_generate_excel(self):
        """Genera el reporte en formato Excel"""
        self.ensure_one()
        
        # Obtener la configuración
        journal_ids = []
        tax_ids = []
        if self.config_id:
            if self.config_id.journal_ids:
                journal_ids = self.config_id.journal_ids.ids
            if self.config_id.report_taxes:
                tax_ids = self.config_id.report_taxes.ids
        
        # Preparar datos para procesar
        datos = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'journal_ids': journal_ids,
            'tax_ids': tax_ids,
        }
        
        # Usar el mismo método de procesamiento que el reporte PDF
        report_model = self.env['report.l10n_hn_fiscal.report_purchase_book']
        result = report_model.process_invoices(datos)
        
        # Obtener el color primario del modelo base.document.layout
        company = self.env.company
        primary_color = None
        
        try:
            document_layout = self.env['base.document.layout'].search([
                ('company_id', '=', company.id)
            ], limit=1)
            
            if document_layout and document_layout.primary_color:
                primary_color = document_layout.primary_color
        except Exception:
            pass
        
        # Si no se encontró el color, usar un gris por defecto
        if not primary_color:
            primary_color = '#D3D3D3'
        
        # Convertir color hex a RGB y aplicar transparencia igual que en el PDF
        rgb_primary = self._hex_to_rgb(primary_color)
        
        # Color para encabezado (alpha 0.25 = 25% color + 75% blanco)
        header_r = int(rgb_primary[0] * 0.25 + 255 * 0.75)
        header_g = int(rgb_primary[1] * 0.25 + 255 * 0.75)
        header_b = int(rgb_primary[2] * 0.25 + 255 * 0.75)
        header_color = f'#{header_r:02x}{header_g:02x}{header_b:02x}'
        
        # Color para totales (alpha 0.45 = 45% color + 55% blanco)
        totals_r = int(rgb_primary[0] * 0.45 + 255 * 0.55)
        totals_g = int(rgb_primary[1] * 0.45 + 255 * 0.55)
        totals_b = int(rgb_primary[2] * 0.45 + 255 * 0.55)
        totals_color = f'#{totals_r:02x}{totals_g:02x}{totals_b:02x}'
        
        # Crear el archivo Excel
        f = io.BytesIO()
        libro = xlsxwriter.Workbook(f)
        hoja = libro.add_worksheet('Libro de Compras')
        
        # Formatos base
        formato_fecha = libro.add_format({
            'num_format': 'dd/mm/yyyy',
            'font_name': 'Arial'
        })
        formato_numero = libro.add_format({
            'num_format': '#,##0.00',
            'font_name': 'Arial'
        })
        formato_datos_texto = libro.add_format({'font_name': 'Arial'})
        
        # Formato para encabezado del reporte (negrita, centrado, todas las columnas)
        formato_encabezado_reporte = libro.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_name': 'Arial',
            'font_size': 11
        })
        
        # Formato para títulos de columnas (negrita, centrado horizontal y vertical, color de fondo)
        formato_encabezado = libro.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': header_color,
            'border': 1,
            'font_name': 'Arial'
        })
        
        # Formato para totales (negrita, números, color de fondo)
        formato_totales = libro.add_format({
            'bold': True,
            'num_format': '#,##0.00',
            'bg_color': totals_color,
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
            'font_name': 'Arial'
        })
        
        # Formato para texto de totales (negrita, color de fondo, centrado)
        formato_texto_totales = libro.add_format({
            'bold': True,
            'bg_color': totals_color,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_name': 'Arial'
        })
        
        # Obtener información de la compañía
        company_rtn = report_model.format_rtn(company.vat) if company.vat else ''
        
        # Formatear fechas usando format_date de Odoo
        fecha_desde_str = format_date(self.env, self.date_from, date_format='dd MMMM yyyy')
        fecha_hasta_str = format_date(self.env, self.date_to, date_format='dd MMMM yyyy')
        
        # Encabezado - Combinar todas las columnas (A:M) para cada fila
        num_columnas = 13  # De A a M (0-12)
        hoja.merge_range(0, 0, 0, num_columnas - 1, company.name or '', formato_encabezado_reporte)
        hoja.merge_range(1, 0, 1, num_columnas - 1, f'RTN: {company_rtn}', formato_encabezado_reporte)
        hoja.merge_range(2, 0, 2, num_columnas - 1, 'REGISTRO DE LIBRO DE COMPRAS', formato_encabezado_reporte)
        hoja.merge_range(3, 0, 3, num_columnas - 1, f'Período: Del {fecha_desde_str} al {fecha_hasta_str}', formato_encabezado_reporte)
        hoja.merge_range(4, 0, 4, num_columnas - 1, 'Expresado en Lempiras', formato_encabezado_reporte)
        
        # Encabezados de columnas
        y = 6
        columnas = [
            'Número', 'Tipo', 'Fecha', 'RTN', 'Nombre/Razón Social del Proveedor',
            'Descripción', 'CAI', 'Número de Documento', 'Importe Exento',
            'Importe Exonerado', 'Importe Gravado', 'Importe del ISV', 'Total'
        ]
        for col_idx, col_name in enumerate(columnas):
            hoja.write(y, col_idx, col_name, formato_encabezado)
        
        # Datos
        y += 1
        for linea in result['lineas']:
            hoja.write(y, 0, y - 6, formato_datos_texto)  # Número de línea
            hoja.write(y, 1, linea['tipo_documento'], formato_datos_texto)
            hoja.write(y, 2, linea['fecha'], formato_fecha)
            hoja.write(y, 3, linea['rtn'], formato_datos_texto)
            hoja.write(y, 4, linea['proveedor'], formato_datos_texto)
            hoja.write(y, 5, linea['descripcion'], formato_datos_texto)
            hoja.write(y, 6, linea['cai'], formato_datos_texto)
            hoja.write(y, 7, linea['numero_correlativo'], formato_datos_texto)
            hoja.write(y, 8, linea['importe_exento'], formato_numero)
            hoja.write(y, 9, linea['importe_exonerado'], formato_numero)
            hoja.write(y, 10, linea['importe_gravado'], formato_numero)
            hoja.write(y, 11, linea['importe_isv'], formato_numero)
            hoja.write(y, 12, linea['total'], formato_numero)
            y += 1
        
        # Fila de totales - Combinar columnas A:H (0-7) para "TOTALES:"
        hoja.merge_range(y, 0, y, 7, 'TOTALES:', formato_texto_totales)
        hoja.write(y, 8, result['totales']['total_exento'], formato_totales)
        hoja.write(y, 9, result['totales']['total_exonerado'], formato_totales)
        hoja.write(y, 10, result['totales']['total_gravado'], formato_totales)
        hoja.write(y, 11, result['totales']['total_isv'], formato_totales)
        hoja.write(y, 12, result['totales']['total_general'], formato_totales)
        
        # Ajustar ancho de columnas
        hoja.set_column(0, 0, 10)  # Número
        hoja.set_column(1, 1, 20)  # Tipo
        hoja.set_column(2, 2, 12)  # Fecha
        hoja.set_column(3, 3, 15)  # RTN
        hoja.set_column(4, 4, 30)  # Proveedor
        hoja.set_column(5, 5, 40)  # Descripción
        hoja.set_column(6, 6, 20)  # CAI
        hoja.set_column(7, 7, 18)  # Número Correlativo
        hoja.set_column(8, 12, 15)  # Columnas numéricas
        
        libro.close()
        
        # Guardar el archivo
        datos = base64.b64encode(f.getvalue())
        self.write({
            'archivo': datos,
            'name': 'libro_de_compras.xlsx'
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase_report_wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

