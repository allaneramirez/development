# # -*- coding: utf-8 -*-

from odoo import api, fields, models

class AccountMove(models.Model):
    _inherit = "account.move"

    url = fields.Char(string="URL")