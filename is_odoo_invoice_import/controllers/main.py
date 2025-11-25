# -*- coding: utf-8 -*-
##############################################################################
#
#   Module: odoo_import_invoice
#   File: controllers/main.py
#   Description:
#       Controller providing a secure route for downloading
#       the dynamic Excel example template of the invoice import wizard.
#       This route avoids the issue where the binary field (`files`)
#       becomes disabled after downloading.
#
#   HOW IT WORKS:
#       - The user clicks the "Download Example Template" link.
#       - The route calls the wizard’s internal method `download_template()`
#         (executed in a temporary context).
#       - The generated Excel file is streamed back as an HTTP response,
#         without reloading or duplicating the transient record.
#
#   Updated by: Allan E. Ramírez Madrid / INTEGRALL (2025)
#   License: AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
#
##############################################################################

from odoo import http
from odoo.http import request
import base64

class ImportInvoiceController(http.Controller):
    """Public controller for the Excel template download of the import wizard."""

    @http.route('/odoo_import_invoice/download_template', type='http', auth='user')
    def download_invoice_template(self, **kwargs):
        """
        Generates and returns the Excel example template without affecting
        the wizard record (avoids disabling the Binary field 'files').
        """
        try:
            # Create a transient wizard record just to call the generator
            wizard = request.env['import.invoice.wizard'].sudo().create({})
            result = wizard.download_template()

            # Extract the attachment ID from the URL returned by the wizard method
            attach_id = int(result['url'].split('/')[-1].split('?')[0])
            attachment = request.env['ir.attachment'].sudo().browse(attach_id)

            # Decode the binary data
            file_content = base64.b64decode(attachment.datas or b'')
            file_name = attachment.name or 'invoice_import_template.xlsx'

            # Build the HTTP response for direct download
            return request.make_response(
                file_content,
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', f'attachment; filename="{file_name}"'),
                ]
            )

        except Exception as e:
            # If something goes wrong, return a readable error response
            return request.make_response(
                f"Error generating template: {str(e)}",
                headers=[('Content-Type', 'text/plain; charset=utf-8')],
                status=500
            )
