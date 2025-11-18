# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_hn_cai_id = fields.Many2one(
        'l10n_hn.cai',
        string='CAI Activo',
        help='Configuración de CAI activa para este diario.'
    )

    fiscal_document_type_id = fields.Many2one(
        comodel_name='fiscal_document_type',
        string='Fiscal Document for Sales',
        store=True,
        readonly=True,
        help='Documento Fiscal a utilizar en este diario'
    )

    l10n_hn_sequence_is_fiscal = fields.Boolean(
        string="Secuencia Fiscalizada",
        compute='_compute_sequence_is_fiscal',
        help="Indica si la secuencia de este diario está fiscalizada por un CAI."
    )


    @api.depends('sequence_id.active_sar')
    def _compute_sequence_is_fiscal(self):
        for journal in self:
            journal.l10n_hn_sequence_is_fiscal = journal.sequence_id.active_sar if journal.sequence_id else False