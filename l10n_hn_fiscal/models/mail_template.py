# -*- coding: utf-8 -*-
from odoo import models


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    def generate_email(self, res_ids, fields=None):
        """
        Sobrescribe el método para usar el reporte personalizado cuando se genera
        un email para una factura de venta.
        """
        # Normalizar res_ids: puede ser un recordset, una lista de IDs, o un solo ID
        if hasattr(res_ids, '_name') and res_ids._name == 'account.move':
            # Es un recordset de account.move
            move_ids = res_ids.ids
            moves = res_ids
        elif isinstance(res_ids, (list, tuple)):
            # Es una lista de IDs
            move_ids = res_ids
            moves = self.env['account.move'].browse(res_ids) if res_ids else self.env['account.move']
        else:
            # Es un solo ID
            move_ids = [res_ids]
            moves = self.env['account.move'].browse([res_ids])
        
        # Verificar si es una plantilla de factura y si hay un reporte personalizado configurado
        # Cambiar temporalmente el report_template antes de generar el email
        original_report_template = None
        if self.model == 'account.move' and move_ids:
            # Verificar si todas las facturas tienen el mismo reporte personalizado configurado
            custom_report = None
            all_have_custom = True
            for move in moves:
                if (move.move_type == 'out_invoice' and 
                    move.journal_id.type == 'sale' and 
                    move.company_id.out_invoice_report_to_print):
                    if custom_report is None:
                        custom_report = move.company_id.out_invoice_report_to_print
                    elif custom_report.id != move.company_id.out_invoice_report_to_print.id:
                        all_have_custom = False
                        break
                else:
                    all_have_custom = False
                    break
            
            # Si todas las facturas tienen el mismo reporte personalizado, cambiar temporalmente
            if all_have_custom and custom_report:
                original_report_template = self.report_template
                # Cambiar el report_template temporalmente usando sudo para evitar problemas de permisos
                self.sudo().write({'report_template': custom_report.id})
        
        try:
            # Generar el email con el reporte personalizado (si se cambió)
            # noinspection PyUnresolvedReferences
            result = super().generate_email(move_ids, fields=fields)
        finally:
            # Restaurar el report_template original si se cambió
            if original_report_template is not None:
                if original_report_template:
                    self.sudo().write({'report_template': original_report_template.id})
                else:
                    self.sudo().write({'report_template': False})
        
        return result

