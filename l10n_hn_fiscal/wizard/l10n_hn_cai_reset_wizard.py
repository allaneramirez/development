# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class L10nHnCaiResetWizard(models.TransientModel):
    _name = 'l10n_hn.cai.reset.wizard'
    _description = 'Asistente para Restablecer CAI a Borrador'

    cai_id = fields.Many2one('l10n_hn.cai', string='CAI', readonly=True)
    provided_hash = fields.Char(string='Hash de Confirmación', required=True)

    def action_confirm_reset(self):
        self.ensure_one()
        self.cai_id._reset_to_draft_with_hash(self.provided_hash)
        return {'type': 'ir.actions.act_window_close'}
