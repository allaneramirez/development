# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class IrSequence(models.Model):
    _inherit = "ir.sequence"

    active_sar = fields.Boolean('Documento Fiscal')
    cai = fields.Char('CAI',size=37)
    emition = fields.Date('Fecha de recepcion')
    emition_limit = fields.Date('Fecha limite de emision')
    declaration = fields.Char('Declaracion', size=8)
    range_start = fields.Integer('Numero Inicial')
    range_end = fields.Integer('Numero Final')
    range_start_str = fields.Char('Correlativo Inicial', compute='_get_range_start', store=False)
    range_end_str = fields.Char('Correlativo Final', compute='_get_range_end', store=False)
    fiscal_document_type_id = fields.Many2one('fiscal_document_type', string='Tipo de Documento Fiscal',
                                                  domain="[('country_id.code', '=', 'HN')]")
    l10n_hn_establecimiento_code = fields.Char(string='Código de Establecimiento')
    l10n_hn_punto_emision_code = fields.Char(string='Punto de Emisión')
    
    has_confirmed_cai = fields.Boolean(
        string='Tiene CAI Confirmado',
        compute='_compute_has_confirmed_cai',
        store=False,
        help="Indica si esta secuencia está asociada a un CAI confirmado. Campo auxiliar para restricciones de vista."
    )
    
    def _compute_has_confirmed_cai(self):
        """
        Calcula si la secuencia tiene un CAI confirmado asociado.
        No usa @api.depends porque no puede depender de 'id'.
        Se calcula cada vez que se accede al campo.
        """
        for seq in self:
            if seq.id:
                cai_confirmado = self.env['l10n_hn.cai'].search([
                    ('sequence_id', '=', seq.id),
                    ('state', '=', 'confirmed')
                ], limit=1)
                seq.has_confirmed_cai = bool(cai_confirmado)
            else:
                # Si no tiene id, es un registro nuevo, no puede tener CAI confirmado
                seq.has_confirmed_cai = False

    def write(self, vals):
        if self.env.context.get('allow_cai_write'):
            # El contexto 'allow_cai_write' es usado por el modelo CAI
            # para escribir en la secuencia (ej. al confirmar el CAI).
            # Omitimos el chequeo para permitir que el CAI escriba.
            return super(IrSequence, self).write(vals)

        # Para todas las secuencias que se intentan escribir:
        for seq in self:
            # Solo nos importa si la secuencia está marcada como fiscal (active_sar=True).
            # Si es False, no está gestionada por un CAI, así que se puede editar.
            if seq.active_sar:
                # La secuencia está (o estuvo) asociada a un CAI.
                # Verifiquemos si el CAI asociado *sigue* en estado 'confirmado'.
                cai_confirmado = self.env['l10n_hn.cai'].search([
                    ('sequence_id', '=', seq.id),
                    ('state', '=', 'confirmed')
                ], limit=1)

                if cai_confirmado:
                    # SÍ, existe un CAI confirmado apuntando a esta secuencia.
                    # La secuencia DEBE estar bloqueada (solo lectura).
                    raise UserError(_(
                        "La secuencia '%s' no puede modificarse porque está "
                        "asociada al CAI confirmado '%s'.\n\n"
                        "Para modificar esta secuencia, primero debe restablecer "
                        "el CAI asociado a borrador."
                    ) % (seq.name, cai_confirmado.name))

                # Si llegamos aquí, significa que seq.active_sar es True,
                # pero NO hay un CAI 'confirmed' (probablemente está en 'draft').
                # Por lo tanto, SÍ PERMITIMOS la escritura.

        # Si el bucle termina sin errores, significa que todas las secuencias
        # que se están modificando son editables.
        return super(IrSequence, self).write(vals)

    def unlink(self):
        if any(seq.active_sar for seq in self):
            raise UserError(_("No se puede eliminar una secuencia que está asociada a un CAI activo."))
        return super(IrSequence, self).unlink()


    @api.depends('range_start', 'prefix')
    def _get_range_start(self):
        for rec in self:
            if rec.range_start:
                rec.range_start_str = str(rec.prefix or '') + str(rec.range_start).zfill(8)
            else:
                rec.range_start_str = False

    @api.depends('range_end', 'prefix')
    def _get_range_end(self):
        for rec in self:
            if rec.range_end:
                rec.range_end_str = str(rec.prefix or '') + str(rec.range_end).zfill(8)
            else:
                rec.range_end_str = False

    def _next(self, sequence_date=None):
        """
        Sobrescribe _next para añadir la validación del CAI (range_end)
        ANTES de generar y consumir el número de la secuencia.

        Esta validación se ejecuta ANTES de llamar a super(), actuando como
        una barrera de pre-validación.
        """
        if self.active_sar and self.cai:
            dt = sequence_date or self._context.get('ir_sequence_date', fields.Date.today())

            try:
                current_sequence_obj = self._get_current_sequence(sequence_date=dt)
            except UserError as e:
                _logger.error("Error al obtener la secuencia actual para %s: %s", self.name, e)
                raise
            next_number_to_use = current_sequence_obj.number_next_actual

            # 4. Validar contra el 'range_end' (que está en self, la secuencia principal)
            if self.range_end and next_number_to_use > self.range_end:
                raise UserError(_(
                    'El próximo número de la secuencia (%s) excede el rango '
                    'final del CAI (%s) para la secuencia "%s". '
                    'No se pueden generar más documentos.'
                ) % (next_number_to_use, self.range_end, self.name))
        return super(IrSequence, self)._next(sequence_date=sequence_date)