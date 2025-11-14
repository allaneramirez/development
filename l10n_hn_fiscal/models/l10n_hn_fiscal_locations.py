# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class L10nHnEstablecimiento(models.Model):
    _name = 'l10n_hn.establecimiento'
    _description = 'Establecimientos Fiscales de Honduras'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company
    )

    company_partner_id = fields.Many2one(
        'res.partner',
        string='Partner de la Compañía',
        related='company_id.partner_id',
        store=True,
        readonly=True
    )

    name = fields.Char(string='Nombre Comercial', required=True, tracking=True)
    code = fields.Char(string='Código de Establecimiento', size=3,required=True, tracking=True)

    address_id = fields.Many2one(
        'res.partner',
        string='Dirección Fiscal',
        required=True,
        domain="[('type', '=', 'store'), ('parent_id', '=', company_partner_id)]"
    )

    punto_emision_ids = fields.One2many(
        'l10n_hn.punto.emision',
        'establecimiento_id',
        string='Puntos de Emisión'
    )

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)', 'El código del establecimiento debe ser único por compañía.')
    ]

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
        journals = self.env['account.journal'].search([('l10n_hn_establecimiento_id', 'in', self.ids)])
        if journals:
            raise UserError(
                _('No puede eliminar un establecimiento que está siendo utilizado en uno o más diarios contables.'))
        return super(L10nHnEstablecimiento, self).unlink()


class L10nHnPuntoEmision(models.Model):
    _name = 'l10n_hn.punto.emision'
    _description = 'Puntos de Emisión Fiscal de Honduras'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    establecimiento_id = fields.Many2one('l10n_hn.establecimiento', string='Establecimiento', required=True,
                                         ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Compañía', related='establecimiento_id.company_id', store=True)
    code = fields.Char(string='Código de Punto de Emisión', required=True, size=3, tracking=True)
    name = fields.Char(string='Nombre del Punto de Emisión', required=True, tracking=True)

    _sql_constraints = [
        ('code_establecimiento_uniq', 'unique(code, establecimiento_id)',
         'El código del punto de emisión debe ser único por establecimiento.')
    ]

    def unlink(self):
        # This logic will be completed once the journal model is modified.
        # For now, we prepare the structure.
        journals = self.env['account.journal'].search([('l10n_hn_punto_emision_id', 'in', self.ids)])
        if journals:
            raise UserError(
                _('No puede eliminar un punto de emisión que está siendo utilizado en uno o más diarios contables.'))
        return super(L10nHnPuntoEmision, self).unlink()