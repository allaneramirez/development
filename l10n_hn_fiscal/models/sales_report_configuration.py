# -*- coding: utf-8 -*-
from odoo import fields, models, api
from ..utils import compat


class SalesReportConfiguration(models.Model):
    _name = 'sales_report_configuration'
    _description = 'Configuración de Registro de Compras y Ventas'
    _order = 'report_name, id'

    name = fields.Char(string='Nombre', compute='_compute_name', store=True)
    report_name = fields.Selection([
        ('purchase_report', 'Invoice Purchase Report'),
        ('sales_report', 'Invoice Sales Report'),
    ], string='Tipo de Reporte', required=True, default='sales_report')
    report_taxes = fields.Many2many(
        'account.tax',
        'sales_report_config_tax_rel',
        'config_id',
        'tax_id',
        string='Impuestos'
    )
    journal_ids = fields.Many2many(
        'account.journal',
        'sales_report_config_journal_rel',
        'config_id',
        'journal_id',
        string='Diarios'
    )
    allowed_tax_use = fields.Selection(
        [('sale', 'Ventas'), ('purchase', 'Compras')],
        compute='_compute_allowed_values',
        store=False
    )
    allowed_journal_type = fields.Selection(
        [('sale', 'Ventas'), ('purchase', 'Compras')],
        compute='_compute_allowed_values',
        store=False
    )

    @api.model
    def _get_tax_domain(self, report_name):
        """Retorna el dominio para impuestos según el tipo de reporte"""
        if report_name == 'sales_report':
            return compat.make_tax_domain(self.env, 'sale')
        elif report_name == 'purchase_report':
            return compat.make_tax_domain(self.env, 'purchase')
        return compat.make_tax_domain(self.env, 'both')

    @api.model
    def _get_journal_domain(self, report_name):
        """Retorna el dominio para diarios según el tipo de reporte"""
        if report_name == 'sales_report':
            return compat.make_journal_domain(self.env, 'sale')
        elif report_name == 'purchase_report':
            return compat.make_journal_domain(self.env, 'purchase')
        # Por defecto permitir ambos tipos si no se reconoce el reporte
        sale_domain = compat.make_journal_domain(self.env, 'sale')
        purchase_domain = compat.make_journal_domain(self.env, 'purchase')
        if sale_domain and purchase_domain:
            return ['|'] + sale_domain + purchase_domain
        return []

    @api.depends('report_name')
    def _compute_name(self):
        for rec in self:
            if rec.report_name == 'sales_report':
                rec.name = 'Invoice Sales Report'
            elif rec.report_name == 'purchase_report':
                rec.name = 'Invoice Purchase Report'
            else:
                rec.name = 'Sin nombre'

    @api.depends('report_name')
    def _compute_allowed_values(self):
        for rec in self:
            if rec.report_name == 'sales_report':
                rec.allowed_tax_use = 'sale'
                rec.allowed_journal_type = 'sale'
            else:
                rec.allowed_tax_use = 'purchase'
                rec.allowed_journal_type = 'purchase'

    @api.onchange('report_name')
    def _onchange_report_name(self):
        """Actualiza el dominio de journal_ids y report_taxes según el tipo de reporte y limpia la selección"""
        if self.report_name == 'sales_report':
            # Para reporte de ventas, solo diarios de tipo venta e impuestos de venta
            # Limpiar diarios que no sean de venta
            self.journal_ids = compat.filter_journals_by_type(self.journal_ids, 'sale')
            # Limpiar impuestos que no sean de venta
            self.report_taxes = compat.filter_taxes_by_scope(self.report_taxes, 'sale')
            return {
                'domain': {
                    'journal_ids': self._get_journal_domain('sales_report'),
                    'report_taxes': self._get_tax_domain('sales_report')
                }
            }
        elif self.report_name == 'purchase_report':
            # Para reporte de compras, solo diarios de tipo compra e impuestos de compra
            # Limpiar diarios que no sean de compra
            self.journal_ids = compat.filter_journals_by_type(self.journal_ids, 'purchase')
            # Limpiar impuestos que no sean de compra
            self.report_taxes = compat.filter_taxes_by_scope(self.report_taxes, 'purchase')
            return {
                'domain': {
                    'journal_ids': self._get_journal_domain('purchase_report'),
                    'report_taxes': self._get_tax_domain('purchase_report')
                }
            }
        return {
            'domain': {
                'journal_ids': self._get_journal_domain(self.report_name),
                'report_taxes': self._get_tax_domain(self.report_name)
            }
        }

    def action_generate_sales_report(self):
        """Abre el wizard para generar el reporte de ventas"""
        self.ensure_one()
        if self.report_name != 'sales_report':
            return False
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Generar Reporte de Ventas',
            'res_model': 'sales_report_wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_config_id': self.id,
            }
        }

    def action_generate_purchase_report(self):
        """Abre el wizard para generar el reporte de compras"""
        self.ensure_one()
        if self.report_name != 'purchase_report':
            return False
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Generar Reporte de Compras',
            'res_model': 'purchase_report_wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_config_id': self.id,
            }
        }

