# -*- coding: utf-8 -*-
import uuid
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class L10nHnCai(models.Model):
    _name = 'l10n_hn.cai'
    _description = 'Configuración de CAI para Honduras'
    _order = 'create_date desc'

    name = fields.Char(
        string='CAI', required=True, copy=False,
        help="Clave de Autorización de Impresión otorgada por la autoridad fiscal."
    )
    active = fields.Boolean(
        string='Activo', default=True,
        help="Desmarque esta casilla para desactivar el CAI sin eliminarlo."
    )
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
    ], string='Estado', default='draft', readonly=True, copy=False, tracking=True)

    journal_id = fields.Many2one(
        'account.journal', string='Diario', required=True,
        domain="[('type', '=', 'sale'), ('l10n_latam_use_documents', '=', True)]",
        help="Diario contable al que se aplicará esta configuración de CAI."
    )
    sequence_id = fields.Many2one(
        'ir.sequence', string='Secuencia', required=True,
        help="Secuencia que será actualizada con los datos de este CAI al confirmar."
    )

    l10n_latam_document_type_id = fields.Many2one(
        'l10n_latam.document.type', string='Tipo de Documento Fiscal',
        required=True, domain="[('country_id.code', '=', 'HN')]",
        help="Tipo de documento de LATAM que corresponde a este CAI."
    )

    emition = fields.Date(string='Fecha de recepción', required=True)
    emition_limit = fields.Date(string='Fecha límite de emisión', required=True)
    range_start = fields.Integer(string='Número Inicial', required=True)
    range_end = fields.Integer(string='Número Final', required=True)
    declaration = fields.Char(string='Declaración', size=8, help="Campo para la declaración fiscal, si aplica.")

    establecimiento_id = fields.Many2one(
        'l10n_hn.establecimiento',
        string='Código de Establecimiento',
        required=True,
        tracking=True
    )
    punto_emision_id = fields.Many2one(
        'l10n_hn.punto.emision',
        string='Punto de Emisión',
        required=True,
        domain="[('establecimiento_id', '=', establecimiento_id)]",
        tracking=True
    )
    digitos_correlativo = fields.Integer(string='Dígitos del Correlativo', default=8, required=True)

    confirmation_hash = fields.Char(
        string='Hash de Confirmación', readonly=True, copy=False,
        help="Hash de seguridad generado al confirmar. Necesario para restablecer a borrador."
    )

    # Related fields for display purposes
    journal_type = fields.Selection(related='journal_id.type', string='Tipo de Diario', readonly=True)
    journal_code = fields.Char(related='journal_id.code', string='Código del Diario', readonly=True)

    # Ahora almacenado (store=True) para permitir actualizarlo desde hooks (ej. al publicar facturas)
    sequence_last_number = fields.Integer(
        string='Último Número Real Usado',
        compute='_compute_sequence_last_number',
        store=True,
        readonly=True,
        help="Último número de factura real encontrado en el sistema para el diario asociado."
    )

    remaining_numbers = fields.Integer(
        string='Números Restantes',
        compute='_compute_remaining_numbers',
        readonly=True,
        help="Cantidad de números fiscales disponibles en el rango de CAI actual."
    )

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'El número de CAI debe ser único.'),
        ('sequence_id_active_uniq', 'unique(sequence_id, active)',
         'Una secuencia solo puede estar asociada a un CAI activo a la vez.'),
    ]

    @api.depends('journal_id', 'journal_id.company_id')
    def _compute_sequence_last_number(self):
        """
        Compute stored: obtiene el último número usado (numérico) para el diario.
        Usa la consulta SQL que extrae la porción numérica final de l10n_latam_document_number.
        NOTA: Este campo es store=True y además puede actualizarse desde hooks (ej. al publicar).
        """
        for rec in self:
            if not rec.journal_id:
                rec.sequence_last_number = 0
                continue
            try:
                last_num = rec._get_last_number_for_journal(rec.journal_id)
                rec.sequence_last_number = last_num or 0
            except Exception as e:
                _logger.exception("Error computando sequence_last_number para CAI %s: %s", rec.id, e)
                rec.sequence_last_number = 0

    def _get_last_number_for_journal(self, journal):
        """
        Helper that runs a SQL query to extract the maximum numeric suffix from
        account.move.l10n_latam_document_number for posted customer invoices/refunds
        on the given journal. Returns an int or 0/None.
        """
        self.ensure_one()  # to have env/cr available in recordset
        if not journal:
            return 0

        # Considerar tipos de movimiento cliente (ajustar si se requiere otro conjunto)
        move_types = ('out_invoice', 'out_refund')

        params = [journal.id, move_types]
        company_clause = ""
        # If the journal has a company, limit by it to avoid cross-company noise
        if getattr(journal, 'company_id', False):
            company_clause = " AND company_id = %s"
            params.append(journal.company_id.id)

        # Query: captura los dígitos al final de la cadena y obtiene el máximo numérico.
        # regexp_match devuelve un array; (regexp_match(...))[1] obtiene el grupo capturado.
        query = f"""
            SELECT MAX( (regexp_match(name, '(\\d+)$'))[1]::bigint )
            FROM account_move
            WHERE journal_id = %s
              AND state = 'posted'
              AND move_type IN %s
              AND name IS NOT NULL
              {company_clause}
        """

        # Ejecutar de forma segura con parámetros
        try:
            self.env.cr.execute(query, params)
            res = self.env.cr.fetchone()
            if res and res[0] is not None:
                return int(res[0])
            return 0
        except Exception as e:
            # Loggear el error y propagar/retornar 0 para evitar romper procesos de posteo.
            _logger.exception("Error SQL obteniendo último número para journal %s: %s", journal.id, e)
            return 0

    def _update_cai_last_number(self):
        """
        Recalcula y guarda (write) sequence_last_number para cada registro del CAI.
        Puede llamarse desde hooks (ej. al publicar facturas) o manualmente.
        """
        for rec in self:
            if not rec.journal_id:
                continue
            try:
                new_last = rec._get_last_number_for_journal(rec.journal_id) or 0
                # Al ser store=True, podemos escribir directamente para persistir el valor.
                rec.write({'sequence_last_number': new_last})
                _logger.info("CAI %s (id:%s) actualizado: último número = %s", rec.name, rec.id, new_last)
            except Exception as e:
                _logger.exception("Error actualizando sequence_last_number para CAI %s: %s", rec.id, e)

    @api.depends('range_end', 'range_start', 'sequence_id.use_date_range', 'sequence_id.number_next_actual',
                 'sequence_id.date_range_ids.number_next_actual')
    def _compute_remaining_numbers(self):
        """
        Calculates the remaining numbers in the CAI range.
        It correctly handles sequences with date ranges.
        """
        for rec in self:
            if not rec.range_end or not rec.sequence_id:
                rec.remaining_numbers = 0
                continue

            sequence = rec.sequence_id
            next_number = 0

            if sequence.use_date_range:
                today = fields.Date.context_today(rec)
                date_range = self.env['ir.sequence.date_range'].search([
                    ('sequence_id', '=', sequence.id),
                    ('date_from', '<=', today),
                    ('date_to', '>=', today),
                ], order='date_from desc', limit=1)
                if date_range:
                    next_number = date_range.number_next_actual
            else:
                next_number = sequence.number_next_actual or 0

            # If next_number is not set or is before the start of the range,
            # consider the next number to be the start of the range.
            if next_number < rec.range_start:
                next_number = rec.range_start

            if next_number > rec.range_end:
                rec.remaining_numbers = 0
            else:
                rec.remaining_numbers = rec.range_end - next_number + 1

    @api.constrains('range_start', 'range_end')
    def _check_range(self):
        for rec in self:
            if rec.range_start <= 0 or rec.range_end <= 0:
                raise ValidationError(_("Los rangos de numeración deben ser mayores a cero."))
            if rec.range_start > rec.range_end:
                raise ValidationError(_("El número inicial del rango no puede ser mayor que el número final."))

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        """
        When the journal is selected, automatically set the corresponding sequence,
        update the last number used, and apply a domain to the sequence field.
        """
        if self.journal_id:
            self.sequence_id = self.journal_id.sequence_id
            try:
                last_num = self._get_last_number_for_journal(self.journal_id)
                self.sequence_last_number = last_num or 0
            except Exception as e:
                _logger.exception("Error getting last number on journal change for CAI: %s", e)
                self.sequence_last_number = 0
            return {'domain': {'sequence_id': [('id', '=', self.journal_id.sequence_id.id)]}}
        else:
            self.sequence_id = False
            self.sequence_last_number = 0
            return {'domain': {'sequence_id': []}}

    def confirm_cai(self):
        self.ensure_one()
        if not self.env.user.has_group('l10n_hn_fiscal.group_confirm_cai'):
            raise UserError(_('No tienes permisos para confirmar un CAI.'))

        # Validate that the sequence is not already used by another active CAI
        if self.sequence_id.active_sar and self.sequence_id.cai:
             # Check if there is another active CAI using this sequence
            other_cai = self.env['l10n_hn.cai'].search([
                ('sequence_id', '=', self.sequence_id.id),
                ('id', '!=', self.id),
                ('active', '=', True),
            ], limit=1)
            if other_cai:
                raise UserError(_(
                    "La secuencia seleccionada ('%s') ya está siendo utilizada por otro CAI activo ('%s'). "
                    "Por favor, seleccione una secuencia diferente o cree una nueva."
                ) % (self.sequence_id.name, other_cai.name))

        # Generate hash (if it's the first confirmation)
        if not self.confirmation_hash:
            self.confirmation_hash = uuid.uuid4().hex

        # Construct prefix
        prefix = '-'.join(filter(None, [
            self.establecimiento_id.code,
            self.punto_emision_id.code,
            self.l10n_latam_document_type_id.code
        ]))
        if prefix:
            prefix += '-'

        # Prepare sequence values
        sequence_vals = {
            'cai': self.name,
            'declaration': self.declaration,
            'emition': self.emition,
            'emition_limit': self.emition_limit,
            'range_start': self.range_start,
            'range_end': self.range_end,
            'l10n_latam_document_type_id': self.l10n_latam_document_type_id.id,
            'l10n_hn_establecimiento_code': self.establecimiento_id.code,
            'l10n_hn_punto_emision_code': self.punto_emision_id.code,
            'prefix': prefix,
            'padding': self.digitos_correlativo,
            'use_date_range': True,
            'active_sar': True,
        }
        self.sequence_id.with_context(allow_cai_write=True).write(sequence_vals)

        # Handle date range
        # Search for an existing date range for the same period to avoid duplicates
        date_range = self.env['ir.sequence.date_range'].search([
            ('sequence_id', '=', self.sequence_id.id),
            ('date_from', '=', self.emition),
            ('date_to', '=', self.emition_limit),
        ], limit=1)
        
        if date_range:
            date_range.write({'number_next_actual': self.range_start})
        else:
            self.env['ir.sequence.date_range'].create({
                'sequence_id': self.sequence_id.id,
                'date_from': self.emition,
                'date_to': self.emition_limit,
                'number_next_actual': self.range_start,
            })

        # Set state confirmed
        self.write({'state': 'confirmed'})

        # Al confirmar, actualizar inmediatamente el último número desde las facturas existentes.
        try:
            self._update_cai_last_number()
        except Exception as e:
            # No impedimos la confirmación en caso de error; lo registramos.
            _logger.exception("Error actualizando último número tras confirmar CAI %s: %s", self.id, e)

    def action_reset_to_draft(self):
        # This will open a wizard to ask for the hash
        return {
            'type': 'ir.actions.act_window',
            'name': _('Restablecer a Borrador'),
            'res_model': 'l10n_hn.cai.reset.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_cai_id': self.id},
        }

    def _reset_to_draft_with_hash(self, provided_hash):
        self.ensure_one()
        if not self.env.user.has_group('l10n_hn_fiscal.group_confirm_cai'):
            raise UserError(_('No tienes permisos para restablecer un CAI.'))

        if self.confirmation_hash != provided_hash:
            raise UserError(_('El hash introducido no es correcto. No se puede restablecer el CAI.'))

        self.write({'state': 'draft'})

    def action_recalculate_last_number(self):
        """
        Método público para recalcular manualmente el último número y notificar al usuario.
        Útil para debugging o cuando se detecten inconsistencias en la numeración.
        """
        self._update_cai_last_number()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Recalculado correctamente'),
                'message': _('El último número de factura ha sido actualizado.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def unlink(self):
        for rec in self:
            if rec.confirmation_hash:
                raise UserError(
                    _('No se puede eliminar un CAI que ya ha sido confirmado, incluso si está en estado de borrador.'))
        return super(L10nHnCai, self).unlink()

    def write(self, vals):
        for rec in self:
            if rec.state == 'confirmed':
                # Allow only state changes (from draft to confirmed or vice-versa via wizard)
                # or changes to the 'active' field.
                allowed_changes = {'state', 'active'}
                if any(key not in allowed_changes for key in vals):
                    raise UserError(
                        _('No se pueden modificar los campos de un CAI confirmado. Primero debe restablecerlo a borrador.'))
        return super(L10nHnCai, self).write(vals)
