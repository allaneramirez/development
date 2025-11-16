# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class IrSequence(models.Model):
    _inherit = "ir.sequence"

    active_sar = fields.Boolean('Documento Fiscal')
    cai = fields.Char('CAI',size=37)
    emition = fields.Date('Fecha de recepcion')
    emition_limit = fields.Date('Fecha limite de emision')
    declaration = fields.Char('Declaracion', size=8)
    range_start = fields.Integer('Numero Inicial')
    range_end = fields.Integer('Numero Final')
    range_start_str = fields.Char('Correlativo Inicial', compute='_get_range_start')
    range_end_str = fields.Char('Correlativo Final', compute='_get_range_end')
    l10n_latam_document_type_id = fields.Many2one('l10n_latam.document.type', string='Tipo de Documento Fiscal', 
                                                  domain="[('country_id.code', '=', 'HN')]")
    l10n_hn_establecimiento_code = fields.Char(string='Código de Establecimiento')
    l10n_hn_punto_emision_code = fields.Char(string='Punto de Emisión')

    def write(self, vals):
        if not self.env.context.get('allow_cai_write'):
            for seq in self:
                if seq.active_sar:
                    raise UserError(_("Esta secuencia ha sido asociada a un CAI por lo que no puede modificarse, para modificar sus valores antes tiene que modificar el CAI asociado."))
        return super(IrSequence, self).write(vals)

    def unlink(self):
        if any(seq.active_sar for seq in self):
            raise UserError(_("No se puede eliminar una secuencia que está asociada a un CAI activo."))
        return super(IrSequence, self).unlink()


    def _get_range_start(self):
        if self.range_start:
            self.range_start_str = str(self.prefix) + str(self.range_start).zfill(8)
        else:
            self.range_start_str = False

    def _get_range_end(self):
        if self.range_end:
            self.range_end_str = str(self.prefix) + str(self.range_end).zfill(8)
        else:
            self.range_end_str = False

    def _next(self, sequence_date=None):
        if self.active_sar and self.cai:
            # Determine the next number to be used
            if self.use_date_range:
                date_range = self.env['ir.sequence.date_range'].search([
                    ('sequence_id', '=', self.id),
                    ('date_from', '<=', sequence_date or fields.Date.today()),
                    ('date_to', '>=', sequence_date or fields.Date.today()),
                ], limit=1)
                next_number = date_range.number_next_actual if date_range else self.number_next_actual
            else:
                next_number = self.number_next_actual

            # Validate if the next number exceeds the allowed range
            if next_number > self.range_end:
                raise UserError(_(
                    'El próximo número de la secuencia (%s) excede el rango final del CAI (%s). '
                    'No se pueden generar más documentos con esta secuencia.'
                ) % (next_number, self.range_end))

        return super(IrSequence, self)._next(sequence_date=sequence_date)
