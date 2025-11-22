# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class L10nHnEstablecimiento(models.Model):
    _name = 'l10n_hn.establecimiento'
    _description = 'Establecimientos Fiscales de Honduras'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=False,
        default=lambda self: self.env.company
    )

    company_partner_id = fields.Many2one(
        'res.partner',
        string='Partner de la Compañía',
        related='company_id.partner_id',
        store=True,
        readonly=True
    )

    name = fields.Char(string='Nombre Comercial', required=False, tracking=True)
    code = fields.Char(string='Código de Establecimiento', size=3, required=False, tracking=True)

    address_id = fields.Many2one(
        'res.partner',
        string='Dirección Fiscal',
        required=False,
        domain="[('parent_id', '=', company_partner_id)]"
    )

    punto_emision_ids = fields.One2many(
        'l10n_hn.punto.emision',
        'establecimiento_id',
        string='Puntos de Emisión'
    )

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)', 'El código del establecimiento debe ser único por compañía.')
    ]

    @api.constrains('name', 'code', 'address_id', 'company_id')
    def _check_required_fields(self):
        """Valida que los campos requeridos estén llenos solo si la compañía es de Honduras."""
        for rec in self:
            company_country = rec.company_id.country_id if rec.company_id else False
            if not company_country or company_country.code != 'HN':
                # Si no es Honduras, no validar campos requeridos
                continue
            
            # Validar campos requeridos solo para Honduras
            if not rec.name:
                raise ValidationError(_("El nombre comercial es requerido."))
            if not rec.code:
                raise ValidationError(_("El código de establecimiento es requerido."))
            if not rec.address_id:
                raise ValidationError(_("La dirección fiscal es requerida."))
            if not rec.company_id:
                raise ValidationError(_("La compañía es requerida."))

    # --- INICIO DE LA NUEVA FUNCIÓN ---

    @api.onchange('address_id')
    def _onchange_address_id(self):
        if not self.address_id:
            return

        partner = self.address_id
        nombre_a_usar = partner.tax_licenced_name or partner.name
        codigo_a_usar = False
        if hasattr(partner, 'store_tax_code') and partner.store_tax_code:
            codigo_a_usar = partner.store_tax_code
        if nombre_a_usar and codigo_a_usar:
            self.name = nombre_a_usar
            self.code = codigo_a_usar


    def unlink(self):
        cais = self.env['l10n_hn.cai'].search([('establecimiento_id','=',self.id)])
        if cais:
            cai_names = ', '.join(cais.mapped('name'))
            raise UserError(
                _('No puede eliminar el establecimiento "%s" porque ya esta siendo utilizado en las siguientes configuraciones de CAI: %s') %
                (self.name, cai_names)
            )
        return super(L10nHnEstablecimiento, self).unlink()

class L10nHnPuntoEmision(models.Model):
    _name = 'l10n_hn.punto.emision'
    _description = 'Puntos de Emisión Fiscal de Honduras'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    establecimiento_id = fields.Many2one('l10n_hn.establecimiento', string='Establecimiento', required=False,
                                         ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Compañía', related='establecimiento_id.company_id', store=True)
    code = fields.Char(string='Código de Punto de Emisión', required=False, size=3, tracking=True)
    name = fields.Char(string='Nombre del Punto de Emisión', required=False, tracking=True)

    _sql_constraints = [
        ('code_establecimiento_uniq', 'unique(code, establecimiento_id)',
         'El código del punto de emisión debe ser único por establecimiento.')
    ]

    @api.constrains('name', 'code', 'establecimiento_id')
    def _check_required_fields(self):
        """Valida que los campos requeridos estén llenos solo si la compañía es de Honduras."""
        for rec in self:
            company_country = rec.company_id.country_id if rec.company_id else False
            if not company_country or company_country.code != 'HN':
                # Si no es Honduras, no validar campos requeridos
                continue
            
            # Validar campos requeridos solo para Honduras
            if not rec.name:
                raise ValidationError(_("El nombre del punto de emisión es requerido."))
            if not rec.code:
                raise ValidationError(_("El código de punto de emisión es requerido."))
            if not rec.establecimiento_id:
                raise ValidationError(_("El establecimiento es requerido."))

    def unlink(self):
        cais = self.env['l10n_hn.cai'].search([('punto_emision_id', '=', self.id)])
        if cais:
            cai_names = ', '.join(cais.mapped('name'))
            raise UserError(
                _('No puede eliminar el punto de emisión "%s" porque ya esta siendo utilizado en las siguientes configuraciones de CAI: %s') %
                (self.name, cai_names)
            )
        return super(L10nHnPuntoEmision, self).unlink()