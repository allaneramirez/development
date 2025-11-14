# -*- coding: utf-8 -*-
from odoo import models

class ResCompany(models.Model):
    _inherit = 'res.company'

    def _localization_use_documents(self):
        """
        Honduran localization uses LATAM documents.
        This method is the key to activate the LATAM document functionality
        for companies configured with Honduras as their country.
        """
        self.ensure_one()
        if self.country_id.code == 'HN':
            return True
        return super()._localization_use_documents()
