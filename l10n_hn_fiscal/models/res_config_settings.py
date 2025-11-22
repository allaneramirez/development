# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    out_invoice_report_to_print = fields.Many2one(
        'ir.actions.report',
        string='Reporte de Factura de Venta',
        related='company_id.out_invoice_report_to_print',
        readonly=False,
        domain=[('model', '=', 'account.move'), ('report_type', '=', 'qweb-pdf')],
        help='Seleccione el reporte que se utilizará para imprimir las facturas de venta '
             '(solo facturas asociadas a diarios de tipo venta). Si no se selecciona, '
             'se utilizará el reporte nativo de Odoo.',
    )

