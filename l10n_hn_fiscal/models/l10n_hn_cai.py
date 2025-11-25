# -*- coding: utf-8 -*-
import uuid
import logging
import re
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from ..utils import compat

_logger = logging.getLogger(__name__)


class L10nHnCai(models.Model):
    _name = 'l10n_hn.cai'
    _description = 'Configuración de CAI para Honduras'
    _order = 'create_date desc'

    name = fields.Char(
        string='CAI', required=False, copy=False,
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
        'account.journal', string='Diario', required=False,
        help="Diario contable de tipo venta al que se aplicará esta configuración de CAI."
    )
    company_id = fields.Many2one(
        'res.company', string='Compañía', 
        default=lambda self: self.env.company,
        required=False,
        help="Compañía a la que pertenece este CAI."
    )
    sequence_id = fields.Many2one(
        'ir.sequence', string='Secuencia', required=False,
        help="Secuencia que será actualizada con los datos de este CAI al confirmar."
    )

    fiscal_document_type_id = fields.Many2one(
        'fiscal_document_type', string='Tipo de Documento Fiscal',
        required=False, domain="[('country_id.code', '=', 'HN')]",
        help="Tipo de documento de LATAM que corresponde a este CAI."
    )

    emition = fields.Date(string='Fecha de recepción', required=False)
    emition_limit = fields.Date(string='Fecha límite de emisión', required=False)
    range_start = fields.Integer(string='Número Inicial', required=False)
    range_end = fields.Integer(string='Número Final', required=False)
    declaration = fields.Char(string='Declaración', size=8, help="Campo para la declaración fiscal, si aplica.")

    establecimiento_id = fields.Many2one(
        'l10n_hn.establecimiento',
        string='Código de Establecimiento',
        required=False,
        tracking=True
    )
    punto_emision_id = fields.Many2one(
        'l10n_hn.punto.emision',
        string='Punto de Emisión',
        required=False,
        domain="[('establecimiento_id', '=', establecimiento_id)]",
        tracking=True
    )
    digitos_correlativo = fields.Integer(string='Dígitos del Correlativo', default=8, required=False)

    confirmation_hash = fields.Char(
        string='Hash de Confirmación', readonly=True, copy=False,
        help="Hash de seguridad generado al confirmar. Necesario para restablecer a borrador."
    )

    journal_type = fields.Char(string='Tipo de Diario', compute='_compute_journal_type', store=False, readonly=True)
    journal_code = fields.Char(related='journal_id.code', string='Código del Diario', readonly=True)

    number_next = fields.Integer(
        string='Próximo Número a Emitir',
        compute='_compute_number_next',
        readonly=True,
        store=False,
        help="Próximo número de factura que se emitirá basado en el último número usado con este CAI."
    )

    sequence_last_number = fields.Integer(
        string='Último Número Real Usado',
        compute='_compute_sequence_last_number',
        readonly=True,
        store=False,
        help="Último número de factura real encontrado en el sistema para el diario asociado."
    )

    remaining_numbers = fields.Integer(
        string='Números Restantes',
        compute='_compute_remaining_numbers',
        readonly=True,
        store=False,
        help="Cantidad de números fiscales disponibles en el rango de CAI actual."
    )

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'El número de CAI debe ser único.'),
        ('sequence_id_active_uniq', 'unique(sequence_id, active)',
         'Una secuencia solo puede estar asociada a un CAI activo a la vez.'),
    ]


    @api.constrains('range_start', 'range_end', 'name', 'journal_id', 'sequence_id', 
                    'fiscal_document_type_id', 'emition', 'emition_limit', 
                    'establecimiento_id', 'punto_emision_id', 'digitos_correlativo', 'company_id')
    def _check_required_fields(self):
        """Valida que los campos requeridos estén llenos solo si la compañía es de Honduras."""
        for rec in self:
            company_country = rec.company_id.country_id if rec.company_id else False
            if not company_country or company_country.code != 'HN':
                # Si no es Honduras, no validar campos requeridos
                continue
            
            # Validar campos requeridos solo para Honduras
            if not rec.name:
                raise ValidationError(_("El CAI es requerido."))
            if not rec.journal_id:
                raise ValidationError(_("El diario es requerido."))
            if not rec.sequence_id:
                raise ValidationError(_("La secuencia es requerida."))
            if not rec.fiscal_document_type_id:
                raise ValidationError(_("El tipo de documento fiscal es requerido."))
            if not rec.emition:
                raise ValidationError(_("La fecha de recepción es requerida."))
            if not rec.emition_limit:
                raise ValidationError(_("La fecha límite de emisión es requerida."))
            if not rec.range_start:
                raise ValidationError(_("El número inicial es requerido."))
            if not rec.range_end:
                raise ValidationError(_("El número final es requerido."))
            if not rec.establecimiento_id:
                raise ValidationError(_("El establecimiento es requerido."))
            if not rec.punto_emision_id:
                raise ValidationError(_("El punto de emisión es requerido."))
            if not rec.digitos_correlativo:
                raise ValidationError(_("Los dígitos del correlativo son requeridos."))
            if not rec.company_id:
                raise ValidationError(_("La compañía es requerida."))
            
            # Validar rangos
            if rec.range_start <= 0 or rec.range_end <= 0:
                raise ValidationError(_("Los rangos de numeración deben ser mayores a cero."))
            if rec.range_start > rec.range_end:
                raise ValidationError(_("El número inicial del rango no puede ser mayor que el número final."))

    @api.depends('journal_id')
    def _compute_journal_type(self):
        for rec in self:
            rec.journal_type = compat.get_journal_type_value(rec.journal_id) or ''


    @api.onchange('company_id')
    def _onchange_company_id(self):
        """Actualiza el dominio del journal_id cuando cambia la compañía."""
        domain = []
        sale_domain = compat.make_journal_domain(self.env, 'sale')
        if sale_domain:
            domain.extend(sale_domain)
        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))
        else:
            # Si no hay company_id, usar la compañía del usuario actual
            domain.append(('company_id', '=', self.env.company.id))
        return {'domain': {'journal_id': domain}}

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        """
        When the journal is selected, automatically set the corresponding sequence,
        and apply a domain to the sequence field.
        Note: sequence_last_number is now computed automatically, no need to set it here.
        Also sets the company_id from the journal if not set.
        """
        if self.journal_id:
            # Si no hay company_id, establecerlo desde el journal
            if not self.company_id and self.journal_id.company_id:
                self.company_id = self.journal_id.company_id
            self.sequence_id = self.journal_id.sequence_id
            return {'domain': {'sequence_id': [('id', '=', self.journal_id.sequence_id.id)]}}
        else:
            self.sequence_id = False
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
            self.fiscal_document_type_id.code
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
            'fiscal_document_type_id': self.fiscal_document_type_id.id,
            'l10n_hn_establecimiento_code': self.establecimiento_id.code,
            'l10n_hn_punto_emision_code': self.punto_emision_id.code,
            'prefix': prefix,
            'padding': self.digitos_correlativo,
            'use_date_range': True,
            'active_sar': True,
        }
        self.sequence_id.with_context(allow_cai_write=True).write(sequence_vals)

        # --- MODIFICACIÓN AQUÍ ---
        # Handle date range
        # Solo buscamos si el rango de fechas ya existe.
        date_range = self.env['ir.sequence.date_range'].search([
            ('sequence_id', '=', self.sequence_id.id),
            ('date_from', '=', self.emition),
            ('date_to', '=', self.emition_limit),
        ], limit=1)

        if not date_range:
            # Si NO existe, lo creamos con el number_next_actual según la lógica
            # Si number_next es 0, usamos range_start, si no, usamos number_next
            number_next_actual = self.range_start if self.number_next == 0 else self.number_next
            self.env['ir.sequence.date_range'].create({
                'sequence_id': self.sequence_id.id,
                'date_from': self.emition,
                'date_to': self.emition_limit,
                'number_next_actual': number_next_actual,
            })
        else:
            # Si 'date_range' ya existe, actualizamos number_next_actual según la lógica
            # Si number_next es 0, usamos range_start, si no, usamos number_next
            number_next_actual = self.range_start if self.number_next == 0 else self.number_next
            date_range.write({'number_next_actual': number_next_actual})
        # --- FIN DE LA MODIFICACIÓN ---

        # Set state confirmed
        self.write({'state': 'confirmed'})

        # Los campos compute se actualizarán automáticamente al leer el registro
        # No es necesario llamar a métodos de actualización manual

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
                # Also allow computed fields to be updated automatically
                allowed_changes = {'state', 'active', 'number_next', 'sequence_last_number', 'remaining_numbers'}
                if any(key not in allowed_changes for key in vals):
                    raise UserError(
                        _('No se pueden modificar los campos de un CAI confirmado. Primero debe restablecerlo a borrador.'))
        return super(L10nHnCai, self).write(vals)

    def _get_last_number_for_journal(self, journal):
        """
        Obtiene el último número de factura usado para un diario específico.
        Busca en las facturas publicadas del diario y extrae el número más alto.
        """
        if not journal or not journal.sequence_id:
            return 0

        # Buscar facturas publicadas del diario
        moves = self.env['account.move'].search([
            ('journal_id', '=', journal.id),
            ('state', '=', 'posted'),
            ('name', '!=', '/'),
        ])

        max_number = 0
        for move in moves:
            if move.name:
                # Extraer el número de la factura (última parte numérica)
                match = re.search(r'(\d+)$', move.name)
                if match:
                    try:
                        num = int(match.group(1))
                        if num > max_number:
                            max_number = num
                    except (ValueError, TypeError):
                        continue

        return max_number

    def _get_last_number_for_cai(self):
        """
        Obtiene el último número de factura usado para este CAI específico.
        Busca en las facturas publicadas que tengan el mismo CAI y extrae el número más alto.
        """
        if not self.name:
            return 0

        # Buscar facturas publicadas con el mismo CAI
        moves = self.env['account.move'].search([
            ('cai', '=', self.name),
            ('state', '=', 'posted'),
            ('name', '!=', '/'),
        ])

        max_number = 0
        for move in moves:
            if move.name:
                # Extraer el número de la factura (última parte numérica)
                match = re.search(r'(\d+)$', move.name)
                if match:
                    try:
                        num = int(match.group(1))
                        if num > max_number:
                            max_number = num
                    except (ValueError, TypeError):
                        continue

        return max_number

    @api.depends('name')
    def _compute_number_next(self):
        """
        Calcula el próximo número a emitir basado en el último número usado con este CAI.
        Busca facturas con el mismo CAI, encuentra el número más alto y le suma 1.
        Si no hay facturas con este CAI, retorna 0 (al confirmar se usará range_start).
        Nota: Este campo se recalcula automáticamente cada vez que se accede (store=False).
        """
        for rec in self:
            if rec.name:
                last_num = rec._get_last_number_for_cai()
                # Si hay un último número, el próximo es ese + 1, si no, es 0
                rec.number_next = (last_num + 1) if last_num > 0 else 0
            else:
                rec.number_next = 0

    @api.depends('name', 'journal_id')
    def _compute_sequence_last_number(self):
        """
        Calcula el último número real usado en facturas del diario asociado.
        """
        for rec in self:
            if rec.journal_id:
                try:
                    last_num = rec._get_last_number_for_journal(rec.journal_id)
                    rec.sequence_last_number = last_num or 0
                except Exception as e:
                    _logger.exception("Error computing sequence_last_number for CAI %s: %s", rec.id, e)
                    rec.sequence_last_number = 0
            else:
                rec.sequence_last_number = 0

    @api.depends('number_next', 'range_end')
    def _compute_remaining_numbers(self):
        """
        Calcula los números restantes disponibles en el rango del CAI.
        """
        for rec in self:
            if rec.range_end and rec.number_next:
                remaining = rec.range_end - rec.number_next + 1
                rec.remaining_numbers = max(0, remaining)  # No permitir valores negativos
            else:
                rec.remaining_numbers = 0

