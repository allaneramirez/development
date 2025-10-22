from odoo import models, fields, api, _

class ReportSignatureConfig(models.Model):
    _name = "custom.report.signature"
    _description = "Configuración de Firmas para Reportes"

    report_id = fields.Many2one("account.report", string="Reporte", required=True, ondelete="cascade")
    company_id = fields.Many2one("res.company", string="Compañía", required=True, default=lambda self: self.env.company)
    imagen = fields.Text(string="Imagen (URL o base64)")
    firma1 = fields.Char( string="Nombre quien firma 1")
    firma2 = fields.Char( string="Nombre quien firma 2")
    #firma2_id = fields.Many2one("res.users", string="Nombre quien firma 2")

    _sql_constraints = [
        ('report_company_unique', 'unique(report_id, company_id)', 'Ya existe una configuración para este reporte y compañía.')
    ]

    @api.model
    def create_or_update_signature(self, vals):
        report_id = vals.get('report_id')
        company_id = vals.get('company_id')

        signature = self.search([
            ('report_id', '=', report_id),
            ('company_id', '=', company_id)
        ], limit=1)

        if signature:
            signature.write(vals)
        else:
            signature = self.create(vals)
        return True