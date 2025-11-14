# -*- coding: utf-8 -*-

from odoo import fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    type = fields.Selection(selection_add=[
        ('store', 'Store')
    ], ondelete={'store': 'set default'})

    responsible_name = fields.Char(string="Responsible Name")
    store_tax_code = fields.Char(string="Código de Establecimiento")
    store_licence_number = fields.Char(string="Número de Patente de Comercio")
    tax_licenced_name = fields.Char(string="Nombre Autorizado")

    _sql_constraints = [
        ('store_licence_number_uniq', 'unique(store_licence_number)', '¡El número de patente de comercio ya existe!')
    ]
