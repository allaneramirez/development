from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Texto de Certificación (Nuevo)
    certification_text = fields.Text(related='company_id.certification_text', readonly=False)

    # Firma 1
    sign_img_1 = fields.Binary(related='company_id.sign_img_1', readonly=False)
    name_1 = fields.Char(related='company_id.name_1', readonly=False)
    position_1 = fields.Char(related='company_id.position_1', readonly=False)

    # Firma 2
    sign_img_2 = fields.Binary(related='company_id.sign_img_2', readonly=False)
    name_2 = fields.Char(related='company_id.name_2', readonly=False)
    position_2 = fields.Char(related='company_id.position_2', readonly=False)

    # Firma 3
    sign_img_3 = fields.Binary(related='company_id.sign_img_3', readonly=False)
    name_3 = fields.Char(related='company_id.name_3', readonly=False)
    position_3 = fields.Char(related='company_id.position_3', readonly=False)