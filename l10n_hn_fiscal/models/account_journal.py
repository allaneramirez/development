# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_hn_establecimiento_id = fields.Many2one(
        'l10n_hn.establecimiento',
        string='Establecimiento Fiscal',
        related='l10n_hn_cai_id.establecimiento_id',
        store=True,
        readonly=True,
        help='Establecimiento fiscal asociado a este diario para la facturación en Honduras.'
    )
    l10n_hn_punto_emision_id = fields.Many2one(
        'l10n_hn.punto.emision',
        string='Punto de Emisión Fiscal',
        related='l10n_hn_cai_id.punto_emision_id',
        store=True,
        readonly=True,
        help='Punto de emisión fiscal asociado a este diario para la facturación en Honduras.'
    )
    l10n_hn_cai_id = fields.Many2one(
        'l10n_hn.cai',
        string='CAI Activo',
        compute='_compute_l10n_hn_cai_id',
        store=False, # Not stored, as it's a computed active record
        help='Configuración de CAI activa para este diario.'
    )

    @api.depends('l10n_latam_use_documents')
    def _compute_l10n_hn_cai_id(self):
        for journal in self:
            if journal.l10n_latam_use_documents:
                cai = self.env['l10n_hn.cai'].search([
                    ('journal_id', '=', journal.id),
                    ('state', '=', 'confirmed'),
                    ('active', '=', True)
                ], limit=1)
                journal.l10n_hn_cai_id = cai
            else:
                journal.l10n_hn_cai_id = False

    l10n_hn_sequence_is_fiscal = fields.Boolean(
        string="Secuencia Fiscalizada",
        compute='_compute_sequence_is_fiscal',
        help="Indica si la secuencia de este diario está fiscalizada por un CAI."
    )

    @api.depends('sequence_id.active_sar')
    def _compute_sequence_is_fiscal(self):
        for journal in self:
            journal.l10n_hn_sequence_is_fiscal = journal.sequence_id.active_sar if journal.sequence_id else False
