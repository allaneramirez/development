from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    # Texto de Certificación (Nuevo)
    certification_text = fields.Text(string='Texto de Certificación')

    # Firma 1
    sign_img_1 = fields.Binary(string='Firma 1')
    name_1 = fields.Char(string='Nombre Firmante 1')
    position_1 = fields.Char(string='Cargo Firmante 1')

    # Firma 2
    sign_img_2 = fields.Binary(string='Firma 2')
    name_2 = fields.Char(string='Nombre Firmante 2')
    position_2 = fields.Char(string='Cargo Firmante 2')

    # Firma 3
    sign_img_3 = fields.Binary(string='Firma 3')
    name_3 = fields.Char(string='Nombre Firmante 3')
    position_3 = fields.Char(string='Cargo Firmante 3')