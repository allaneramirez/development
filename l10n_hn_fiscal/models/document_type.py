# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FiscalDocumentType(models.Model):
    _name = 'fiscal_document_type'
    _description = 'Tipo de Documento Fiscal'
    _order = 'sequence'

    sequence = fields.Integer(default=10)
    name = fields.Char(string='Nombre', required=False)
    code = fields.Char(string='Código', size=3, required=False)
    report_name = fields.Char('Name on Reports', help='Name that will be printed in reports, for example "CREDIT NOTE"')
    internal_type = fields.Selection(
        [('invoice', 'Invoices'), ('debit_note', 'Debit Notes'), ('credit_note', 'Credit Notes')],
        help='Analog to odoo account.move.move_type but with more options allowing to identify the kind of document we are'
        ' working with. (not only related to account.move, could be for documents of other models like stock.picking)'
    )
    description = fields.Text(string='Descripción')
    active = fields.Boolean(default=True)
    country_id = fields.Many2one('res.country', string='País', required=False)

    _sql_constraints = [
        ('name_country_uniq', 'unique(name, country_id)', 'El nombre del documento debe ser único por país.'),
        ('code_country_uniq', 'unique(code, country_id)', 'El código del documento debe ser único por país.'),
    ]

    @api.constrains('name', 'code', 'country_id')
    def _check_required_fields(self):
        """Valida que los campos requeridos estén llenos solo si el país es Honduras."""
        for rec in self:
            # Solo validar si el país es Honduras
            if rec.country_id and rec.country_id.code == 'HN':
                if not rec.name:
                    raise ValidationError(_("El nombre es requerido para documentos de Honduras."))
                if not rec.code:
                    raise ValidationError(_("El código es requerido para documentos de Honduras."))
                if not rec.country_id:
                    raise ValidationError(_("El país es requerido para documentos de Honduras."))
