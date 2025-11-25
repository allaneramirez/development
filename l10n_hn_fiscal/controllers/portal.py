# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError, MissingError
from ..utils import compat


class CustomerPortal(CustomerPortal):

    @http.route(['/my/invoices/<int:invoice_id>'], type='http', auth="public", website=True)
    def portal_my_invoice_detail(self, invoice_id, access_token=None, report_type=None, download=False, **kw):
        """
        Sobrescribe el método del portal para usar el reporte personalizado
        cuando se descarga una factura de venta.
        """
        try:
            invoice_sudo = self._document_check_access('account.move', invoice_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # Verificar si es una factura de venta y si hay un reporte personalizado configurado
        if (invoice_sudo.move_type == 'out_invoice' and 
            compat.is_sale_journal(invoice_sudo.journal_id) and 
            invoice_sudo.company_id.out_invoice_report_to_print):
            # Si se solicita el PDF o HTML, usar el reporte personalizado
            if report_type in ('pdf', 'html'):
                # Obtener el XML ID del reporte personalizado
                report = invoice_sudo.company_id.out_invoice_report_to_print
                # Buscar el XML ID del reporte
                xmlid_data = request.env['ir.model.data'].sudo().search([
                    ('model', '=', 'ir.actions.report'),
                    ('res_id', '=', report.id)
                ], limit=1)
                if xmlid_data:
                    report_ref = '%s.%s' % (xmlid_data.module, xmlid_data.name)
                    return self._show_report(
                        model=invoice_sudo,
                        report_type=report_type,
                        report_ref=report_ref,
                        download=download
                    )

        # Si no cumple las condiciones o no es PDF/HTML, usar el comportamiento por defecto
        return super().portal_my_invoice_detail(invoice_id, access_token=access_token, 
                                                 report_type=report_type, download=download, **kw)

