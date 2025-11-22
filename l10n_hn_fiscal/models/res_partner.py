# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    number_sag_hn = fields.Char(string='Número SAG HN')

