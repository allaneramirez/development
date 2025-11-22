# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.exceptions import UserError
import logging
import re

_logger = logging.getLogger(__name__)


class ReportPurchaseBook(models.AbstractModel):
    _name = 'report.l10n_hn_fiscal.report_purchase_book'
    _description = 'Reporte de Libro de Compras Honduras'

    def format_rtn(self, vat):
        """
        Formatea el RTN en formato hondureño: XXXXX-XXXXXX-X
        """
        if not vat:
            return ''
        # Remover guiones y espacios existentes
        vat_clean = vat.replace('-', '').replace(' ', '').strip()
        # Formatear según la longitud
        if len(vat_clean) == 14:
            # Formato: XXXXX-XXXXXX-X
            return f"{vat_clean[:5]}-{vat_clean[5:11]}-{vat_clean[11:]}"
        elif len(vat_clean) == 13:
            # Formato alternativo: XXXXX-XXXXXX-X (sin el último dígito)
            return f"{vat_clean[:5]}-{vat_clean[5:11]}-{vat_clean[11:]}"
        elif len(vat_clean) > 0:
            # Si no tiene 14 dígitos, devolver tal cual (puede estar ya formateado)
            return vat
        return vat

    def hex_to_rgba(self, hex_color, alpha=0.5):
        """
        Convierte un color hex a rgba con transparencia
        """
        if not hex_color:
            # Color por defecto si no hay color primario (gris claro)
            return f'rgba(211, 211, 211, {alpha})'  # Gris claro por defecto
        
        # Si es un string, limpiarlo
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
                return f'rgba({r}, {g}, {b}, {alpha})'
            else:
                # Color por defecto si el formato no es válido
                return f'rgba(211, 211, 211, {alpha})'
        except (ValueError, AttributeError):
            # Color por defecto si hay error al convertir
            return f'rgba(211, 211, 211, {alpha})'

    def _split_ref_parts(self, ref):
        if not ref:
            return '', '', '', ''
        parts = [p for p in re.split(r'\D+', ref) if p]
        while len(parts) < 4:
            parts.append('')
        return parts[0], parts[1], parts[2], parts[-1]

    def process_invoices(self, datos):
        """
        Procesa las facturas de compra y calcula los totales según los impuestos configurados
        """
        totales = {
            'num_facturas': 0,
            'total_exento': 0,
            'total_exonerado': 0,
            'total_gravado': 0,
            'total_isv': 0,
            'total_general': 0,
        }
        
        # Construir el dominio de búsqueda (incluir facturas y notas de crédito de compra en estado posted y cancel)
        domain = [
            ('move_type', 'in', ['in_invoice', 'in_refund']),
            ('state', 'in', ['posted', 'cancel']),
            ('invoice_date', '>=', datos['date_from']),
            ('invoice_date', '<=', datos['date_to']),
        ]
        
        # Filtrar por diarios si están configurados
        if datos.get('journal_ids'):
            domain.append(('journal_id', 'in', datos['journal_ids']))
        
        # Obtener las facturas
        invoices = self.env['account.move'].search(domain, order='invoice_date, name')
        
        # Filtrar por impuestos si están configurados
        if datos.get('tax_ids'):
            tax_ids = datos['tax_ids']
            filtered_invoices = self.env['account.move']
            for invoice in invoices:
                # Verificar si alguna línea tiene alguno de los impuestos configurados
                if invoice.invoice_line_ids.filtered(lambda l: any(tax.id in tax_ids for tax in l.tax_ids)):
                    filtered_invoices |= invoice
            invoices = filtered_invoices
        
        lineas = []
        detalle_isv = []
        invoice_names_in_report = set()
        for invoice in invoices:
            totales['num_facturas'] += 1
            
            # Determinar el tipo de documento fiscal
            # Prioridad: fiscal_document_type_id si está completo, sino deducir del move_type
            if invoice.fiscal_document_type_id and invoice.fiscal_document_type_id.name:
                tipo_documento = invoice.fiscal_document_type_id.name
            else:
                # Deducir del move_type
                if invoice.move_type == 'in_invoice':
                    tipo_documento = 'Factura'
                elif invoice.move_type == 'in_refund':
                    tipo_documento = 'Nota de Crédito'
                else:
                    tipo_documento = 'Documento'
            
            # Si el documento está cancelado, agregar "Anulada" al tipo
            if invoice.state == 'cancel':
                tipo_documento = tipo_documento + ' Anulada'
            
            # Calcular totales por factura
            invoice_exento = 0
            invoice_exonerado = 0
            invoice_gravado = 0
            invoice_gravado_isv15 = 0
            invoice_gravado_isv18 = 0
            invoice_isv = 0
            invoice_isv15 = 0
            invoice_isv18 = 0
            
            # Procesar cada línea de la factura
            for line in invoice.invoice_line_ids:
                line_exento = 0
                line_exonerado = 0
                line_gravado = 0
                line_isv = 0
                
                # Calcular impuestos usando compute_all
                precio = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                r = line.tax_ids.compute_all(
                    precio, 
                    currency=invoice.currency_id, 
                    quantity=line.quantity, 
                    product=line.product_id, 
                    partner=invoice.partner_id
                )
                
                # Verificar los impuestos de la línea
                tax_names = [tax.name for tax in line.tax_ids]
                has_exe = 'EXE' in tax_names
                has_exo = 'EXO' in tax_names
                has_isv15 = 'ISV15' in tax_names
                has_isv18 = 'ISV18' in tax_names
                
                # Para notas de crédito, los valores deben ser negativos
                signo = -1 if invoice.move_type == 'in_refund' else 1
                
                # Calcular según el tipo de impuesto
                if has_exe:
                    line_exento = r['total_excluded'] * signo
                elif has_exo:
                    line_exonerado = r['total_excluded'] * signo
                elif has_isv15 or has_isv18:
                    # Para ISV, usar total_excluded como base gravada
                    line_gravado = r['total_excluded'] * signo
                    # Calcular ISV de los impuestos calculados
                    for tax_data in r['taxes']:
                        tax = self.env['account.tax'].browse(tax_data['id'])
                        if tax.name in ['ISV15', 'ISV18']:
                            amount = tax_data['amount'] * signo
                            line_isv += amount
                            if tax.name == 'ISV15':
                                invoice_gravado_isv15 += r['total_excluded'] * signo
                                invoice_isv15 += amount
                            else:
                                invoice_gravado_isv18 += r['total_excluded'] * signo
                                invoice_isv18 += amount
                else:
                    # Si no tiene impuestos, es exento
                    line_exento = r['total_excluded'] * signo
                
                # Acumular en la factura
                invoice_exento += line_exento
                invoice_exonerado += line_exonerado
                invoice_gravado += line_gravado
                invoice_isv += line_isv
            
            # Si el documento está cancelado, todos los valores deben ser 0.00
            if invoice.state == 'cancel':
                invoice_exento = 0.0
                invoice_exonerado = 0.0
                invoice_gravado = 0.0
                invoice_gravado_isv15 = 0.0
                invoice_gravado_isv18 = 0.0
                invoice_isv = 0.0
                invoice_isv15 = 0.0
                invoice_isv18 = 0.0
                invoice_total = 0.0
            else:
                # Calcular total de la factura
                invoice_total = invoice_exento + invoice_exonerado + invoice_gravado + invoice_isv
            
            # Obtener descripción concatenada de todas las líneas
            description = ', '.join([line.name or '' for line in invoice.invoice_line_ids])
            if len(description) > 100:
                description = description[:100] + '...'
            
            establishment, emission_point, doc_type_chunk, correlativo_chunk = self._split_ref_parts(invoice.ref)
            tax_move_lines = invoice.line_ids.filtered(lambda l: l.tax_line_id and l.tax_line_id.name in ['ISV15', 'ISV18'])
            isv_account_move = sum(abs(line.balance) for line in tax_move_lines)
            isv_diff = isv_account_move - abs(invoice_isv15 + invoice_isv18)

            debit_lines = []
            credit_lines = []
            for line in invoice.line_ids:
                account_code = line.account_id.code or ''
                account_name = line.account_id.name or ''
                if line.debit:
                    debit_lines.append(f"[{account_code}] {account_name} = {line.debit:.2f}")
                if line.credit:
                    credit_lines.append(f"[{account_code}] {account_name} = {line.credit:.2f}")

            for move_line in tax_move_lines:
                detalle_isv.append({
                    'fecha': move_line.date or invoice.date or invoice.invoice_date,
                    'asiento': move_line.move_id.name or '',
                    'monto': abs(move_line.balance),
                    'tax': move_line.tax_line_id.name or '',
                })

            linea = {
                'tipo_documento': tipo_documento,
                'numero': invoice.name or '',
                'fecha': invoice.invoice_date,
                'emition_limit': invoice.emition_limit,
                'rtn': invoice.partner_id.vat or '',
                'proveedor': invoice.partner_id.name or '',
                'descripcion': description,
                'cai': invoice.cai or '',
                'numero_correlativo': invoice.ref or invoice.name or '',
                'importe_exento': invoice_exento,
                'importe_exonerado': invoice_exonerado,
                'importe_gravado': invoice_gravado,
                'importe_gravado_isv15': invoice_gravado_isv15,
                'importe_gravado_isv18': invoice_gravado_isv18,
                'importe_isv': invoice_isv,
                'importe_isv15': invoice_isv15,
                'importe_isv18': invoice_isv18,
                'establecimiento': establishment,
                'punto_emision': emission_point,
                'tipo_doc_ref': doc_type_chunk,
                'correlativo_ref': correlativo_chunk,
                'isv_account_move': isv_account_move,
                'isv_diff': isv_diff,
                'asiento_contable': invoice.name or '',
                'detalle_debe': '\n'.join(debit_lines),
                'detalle_haber': '\n'.join(credit_lines),
                'total': invoice_total,
            }
            
            lineas.append(linea)
            if invoice.name:
                invoice_names_in_report.add(invoice.name)
            
            # Acumular totales generales
            totales['total_exento'] += invoice_exento
            totales['total_exonerado'] += invoice_exonerado
            totales['total_gravado'] += invoice_gravado
            totales['total_isv'] += invoice_isv
            totales['total_general'] += invoice_total
        
        # Ordenar las líneas por tipo de documento y luego por fecha
        lineas = sorted(lineas, key=lambda x: (x['tipo_documento'], x['fecha']))

        detalle_isv = [
            d for d in detalle_isv if not d.get('name') or d.get('name') not in invoice_names_in_report
        ]
        detalle_isv = sorted(detalle_isv, key=lambda d: (d.get('fecha') or '', d.get('asiento')))

        return {'lineas': lineas, 'totales': totales, 'detalle_isv': detalle_isv}

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Prepara los valores para el template del reporte
        """
        if not data:
            data = {}
        
        form_data = data.get('form', {})
        
        # Obtener los datos del wizard
        date_from = form_data.get('date_from')
        date_to = form_data.get('date_to')
        folio_inicial = form_data.get('folio_inicial', 1)
        config_id = form_data.get('config_id', [False])[0] if isinstance(form_data.get('config_id'), list) else form_data.get('config_id')
        
        if not date_from or not date_to:
            raise UserError("Debe especificar las fechas desde y hasta.")
        
        # Obtener la configuración
        config = None
        journal_ids = []
        tax_ids = []
        if config_id:
            config = self.env['sales_report_configuration'].browse(config_id)
            if config.journal_ids:
                journal_ids = config.journal_ids.ids
            if config.report_taxes:
                tax_ids = config.report_taxes.ids
        
        # Preparar datos para procesar
        datos = {
            'date_from': date_from,
            'date_to': date_to,
            'journal_ids': journal_ids,
            'tax_ids': tax_ids,
        }
        
        # Procesar las facturas
        result = self.process_invoices(datos)
        
        # Obtener el color primario del modelo base.document.layout
        company = self.env.company
        primary_color = None
        
        # Buscar el registro de base.document.layout para la compañía actual
        try:
            document_layout = self.env['base.document.layout'].search([
                ('company_id', '=', company.id)
            ], limit=1)
            
            if document_layout and document_layout.primary_color:
                primary_color = document_layout.primary_color
        except Exception:
            # Si el modelo no existe o hay algún error, intentar otros métodos
            pass
        
        # Si no se encontró el color, usar un gris por defecto
        if not primary_color:
            primary_color = '#D3D3D3'  # Gris claro por defecto
        
        # Color del encabezado: 25% de transparencia (alpha 0.25)
        header_bg_color = self.hex_to_rgba(primary_color, 0.25)
        
        # Color de los totales: 45% de transparencia (alpha 0.45)
        totals_bg_color = self.hex_to_rgba(primary_color, 0.45)
        
        # Formatear RTN de la compañía
        company_rtn = self.format_rtn(company.vat) if company.vat else ''

        return {
            'doc_ids': docids or [],
            'doc_model': 'purchase_report_wizard',
            'data': form_data,
            'docs': self.env['purchase_report_wizard'].browse(docids) if docids else self.env['purchase_report_wizard'],
            'result': result,
            'folio_inicial': folio_inicial,
            'date_from': date_from,
            'date_to': date_to,
            'current_company_id': company,
            'company_rtn': company_rtn,
            'header_bg_color': header_bg_color,
            'totals_bg_color': totals_bg_color,
        }

