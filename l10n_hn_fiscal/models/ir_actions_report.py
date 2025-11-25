# -*- coding: utf-8 -*-
from odoo import models
import logging
from ..utils import compat

_logger = logging.getLogger(__name__)


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def report_action(self, docids, data=None, config=True, **kwargs):
        """
        Sobrescribe el método para usar el reporte personalizado cuando se imprime
        una factura de venta, incluso si se selecciona un reporte nativo del menú.
        """
        _logger.info("=== report_action CALLED ===")
        _logger.info("Model: %s, docids: %s", self.model, docids)
        
        # Solo procesar si es un reporte de account.move
        if self.model != 'account.move' or not docids:
            _logger.info("Not account.move or no docids, skipping")
            # noinspection PyUnresolvedReferences
            return super().report_action(docids, data=data, config=config, **kwargs)
        
        # Normalizar docids: puede ser un recordset, una lista de IDs, o un solo ID
        if hasattr(docids, '_name') and docids._name == 'account.move':
            move_ids = docids.ids
            moves = docids
        elif isinstance(docids, (list, tuple)):
            move_ids = docids
            moves = self.env['account.move'].browse(docids)
        else:
            move_ids = [docids]
            moves = self.env['account.move'].browse([docids])
        
        # Verificar si hay facturas de venta con reporte personalizado configurado
        custom_report = None
        for move in moves:
            if (move.move_type == 'out_invoice' and 
                compat.is_sale_journal(move.journal_id) and 
                move.company_id.out_invoice_report_to_print):
                # Si este NO es el reporte personalizado mismo, usar el personalizado
                if self.id != move.company_id.out_invoice_report_to_print.id:
                    custom_report = move.company_id.out_invoice_report_to_print
                    break
        
        # Si hay un reporte personalizado configurado y este NO es el reporte personalizado mismo
        if custom_report:
            # Buscar el XML ID del reporte actual para verificar si es nativo
            xmlid_data = self.env['ir.model.data'].search([
                ('model', '=', 'ir.actions.report'),
                ('res_id', '=', self.id)
            ], limit=1)
            
            # Log temporal para debugging
            _logger.info("=== DEBUG REPORT ACTION ===")
            _logger.info("Report ID: %s", self.id)
            _logger.info("Report Name: %s", self.name)
            _logger.info("Report report_name: %s", self.report_name)
            if xmlid_data:
                xmlid = '%s.%s' % (xmlid_data.module, xmlid_data.name)
                _logger.info("XML ID: %s", xmlid)
                _logger.info("Module: %s", xmlid_data.module)
            else:
                _logger.info("No XML ID found")
            _logger.info("Custom Report ID: %s", custom_report.id)
            _logger.info("========================")
            
            # Verificar si es un reporte nativo del módulo 'account'
            if xmlid_data:
                # Es nativo si pertenece al módulo 'account'
                is_native = (xmlid_data.module == 'account')
                _logger.info("Is native (by module): %s", is_native)
            else:
                # Si no tiene XML ID, verificar por el nombre del reporte
                # Los reportes nativos suelen tener 'account.report_invoice' o 'account.account_invoices' en report_name
                report_name = self.report_name or ''
                is_native = (
                    'account.report_invoice' in report_name or 
                    'account.account_invoices' in report_name or
                    self.name in ['Facturas', 'Invoices', 'Facturas sin pago', 'Invoices without payment']
                )
                _logger.info("Is native (by name): %s", is_native)
            
            # Si es nativo, usar el reporte personalizado
            if is_native:
                _logger.info("Intercepting native report, using custom report")
                return custom_report.report_action(move_ids, data=data, config=config, **kwargs)
            else:
                _logger.info("Not intercepting (not native)")
        
        # Si no cumple las condiciones, usar el comportamiento por defecto
        _logger.info("Using default behavior")
        # noinspection PyUnresolvedReferences
        return super().report_action(docids, data=data, config=config, **kwargs)
    
    def _is_invoice_report(self, report_ref):
        """
        Verifica si el report_ref es un reporte nativo de facturas.
        Basado en el método del módulo account nativo.
        """
        # Verificar directamente por el report_ref (puede ser XML ID o report_name)
        if isinstance(report_ref, str):
            # Verificar si es un XML ID de reporte nativo
            if report_ref in ('account.account_invoices', 'account.report_invoice_with_payments'):
                return True
            # Verificar si contiene los nombres de reporte nativos
            if 'account.report_invoice' in report_ref or 'account.account_invoices' in report_ref:
                return True
            # Intentar obtener el reporte por XML ID
            try:
                report = self.env.ref(report_ref, raise_if_not_found=False)
                if report and report.report_name in ('account.report_invoice_with_payments', 'account.report_invoice'):
                    return True
            except Exception:
                pass
            # Intentar buscar por report_name
            try:
                report = self.env['ir.actions.report'].search([
                    ('report_name', '=', report_ref)
                ], limit=1)
                if report and report.report_name in ('account.report_invoice_with_payments', 'account.report_invoice'):
                    return True
            except Exception:
                pass
        # Si report_ref es un recordset, verificar su report_name
        elif hasattr(report_ref, 'report_name'):
            return report_ref.report_name in ('account.report_invoice_with_payments', 'account.report_invoice')
        # Si es self (el reporte actual), verificar su report_name
        elif hasattr(self, 'report_name'):
            return self.report_name in ('account.report_invoice_with_payments', 'account.report_invoice')
        return False
    
    def _render_qweb_pdf(self, report_ref=None, res_ids=None, data=None, **kwargs):
        """
        Sobrescribe el método que realmente genera el PDF para interceptar
        reportes nativos de facturas y reemplazarlos con el reporte personalizado.
        Basado en el método del módulo account nativo.
        """
        _logger.info("=== _render_qweb_pdf CALLED ===")
        _logger.info("report_ref: %s, Model: %s, res_ids: %s, self.id: %s, self.report_name: %s", 
                     report_ref, self.model, res_ids, self.id, self.report_name)
        
        # Verificar si es un reporte nativo de facturas (similar al módulo account)
        is_native_invoice_report = self._is_invoice_report(report_ref)
        _logger.info("Is native invoice report: %s", is_native_invoice_report)
        
        # También verificar por el report_name de self (el reporte actual)
        if not is_native_invoice_report and hasattr(self, 'report_name'):
            is_native_invoice_report = self.report_name in ('account.report_invoice_with_payments', 'account.report_invoice')
            _logger.info("Is native invoice report (by self.report_name): %s", is_native_invoice_report)
        
        # Solo procesar si es un reporte nativo de facturas y es account.move
        if is_native_invoice_report and self.model == 'account.move' and res_ids:
            # Normalizar res_ids
            if isinstance(res_ids, (list, tuple)):
                move_ids = res_ids
                moves = self.env['account.move'].browse(res_ids)
            else:
                move_ids = [res_ids]
                moves = self.env['account.move'].browse([res_ids])
            
            # Verificar si hay facturas de venta con reporte personalizado configurado
            custom_report = None
            for move in moves:
                if (move.move_type == 'out_invoice' and 
                    compat.is_sale_journal(move.journal_id) and 
                    move.company_id.out_invoice_report_to_print):
                    # Si este NO es el reporte personalizado mismo, usar el personalizado
                    if self.id != move.company_id.out_invoice_report_to_print.id:
                        custom_report = move.company_id.out_invoice_report_to_print
                        break
            
            # Si hay un reporte personalizado configurado, usarlo en lugar del nativo
            if custom_report:
                _logger.info("Intercepting native invoice report, using custom report ID: %s", custom_report.id)
                # Obtener el XML ID del reporte personalizado
                custom_xmlid_data = self.env['ir.model.data'].search([
                    ('model', '=', 'ir.actions.report'),
                    ('res_id', '=', custom_report.id)
                ], limit=1)
                if custom_xmlid_data:
                    custom_report_ref = '%s.%s' % (custom_xmlid_data.module, custom_xmlid_data.name)
                    _logger.info("Using custom report with XML ID: %s", custom_report_ref)
                    return custom_report._render_qweb_pdf(custom_report_ref, res_ids=move_ids, data=data, **kwargs)
                else:
                    # Si no tiene XML ID, usar el report_name
                    _logger.info("Using custom report with report_name: %s", custom_report.report_name)
                    return custom_report._render_qweb_pdf(custom_report.report_name, res_ids=move_ids, data=data, **kwargs)
        
        # Si no cumple las condiciones, usar el comportamiento por defecto
        # (incluye la lógica del módulo account para reportes de facturas)
        _logger.info("Using default behavior in _render_qweb_pdf")
        # noinspection PyUnresolvedReferences
        return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data, **kwargs)

