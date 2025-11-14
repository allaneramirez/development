# -*- coding: utf-8 -*-
from odoo import models, api, fields

class ReportSarP(models.TransientModel):
    _name="report.general.wizard"
    _description = "Reporte General"

    fecha_start = fields.Date(string="Fecha Inicio", default=fields.Date.context_today, )
    fecha_end = fields.Date(string="Fecha Final", default=fields.Date.context_today, )
    team = fields.Many2one('crm.team', string='Sales Channel')
    #team = fields.One2many('crm.team','name', string="Canal de ventas")

    def print_report(self):
        data = { 'fecha_start': self.fecha_start, 'fecha_end': self.fecha_end, 'team':self.team }
        return self.env.ref('l10n_hn_fiscal.report_general_print').report_action([],data=data)
