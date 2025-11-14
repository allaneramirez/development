# -*- coding: utf-8 -*-
from odoo import models, api, fields


class ReportSar(models.TransientModel):
    _name = "report.general.wizard.purchase"
    _description = "Reporte General Compras"

    fecha_start = fields.Date(string="Fecha Inicio", default=fields.Date.context_today, )
    fecha_end = fields.Date(string="Fecha Final", default=fields.Date.context_today, )

    def print_report_purchase(self):
        data = {'fecha_start': self.fecha_start, 'fecha_end': self.fecha_end}
        return self.env.ref('l10n_hn_fiscal.report_general_print_purchase').report_action([], data=data)
