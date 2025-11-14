# -*- coding: utf-8 -*-
from odoo import fields, models

class L10nLatamDocumentType(models.Model):
    _inherit = 'l10n_latam.document.type'

    description = fields.Text(string='Descripción Legal')
