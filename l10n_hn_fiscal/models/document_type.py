# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FiscalDocumentType(models.Model):
    _name = 'fiscal_document_type'
    _description = 'Tipo de Documento Fiscal'
    _order = 'sequence'

    sequence = fields.Integer(default=10)
    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código', size=3, required=True)
    report_name = fields.Char('Name on Reports', help='Name that will be printed in reports, for example "CREDIT NOTE"')
    internal_type = fields.Selection(
        [('invoice', 'Invoices'), ('debit_note', 'Debit Notes'), ('credit_note', 'Credit Notes')],
        help='Analog to odoo account.move.move_type but with more options allowing to identify the kind of document we are'
        ' working with. (not only related to account.move, could be for documents of other models like stock.picking)'
    )
    description = fields.Text(string='Descripción')
    active = fields.Boolean(default=True)
    country_id = fields.Many2one('res.country', string='País', required=True)

    _sql_constraints = [
        ('name_country_uniq', 'unique(name, country_id)', 'El nombre del documento debe ser único por país.'),
        ('code_country_uniq', 'unique(code, country_id)', 'El código del documento debe ser único por país.'),
    ]

    def write(self, vals):
        if not self.env.context.get('l10n_hn_fiscal_allow_write_unlink'):
            raise UserError(_('Los tipos de documento no se pueden modificar. Por favor, cree uno nuevo o archive el existente.'))
        return super().write(vals)

    def unlink(self):
        if not self.env.context.get('l10n_hn_fiscal_allow_write_unlink'):
            raise UserError(_('Los tipos de documento no se pueden eliminar. Por favor, archívelos en su lugar.'))
        return super().unlink()
