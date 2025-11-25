# -*- coding: utf-8 -*-
{
    'name': 'Localización Fiscal Hondureña',
    'version': '16.0.10.0',
    'category': 'Account',
    'summary': 'Factura DPS, Libros fiscales, CAI y reportes PT (Odoo 16 & 17) para el SAR',
    'author': 'Allan Ramirez / INTEGRALL',
    'website': 'https://www.integrall.solutions',
    'description': """
Localización Fiscal Hondureña - Módulo completo para cumplimiento con el SAR

Características Principales
---------------------------
- ✅ Compatible con Odoo 16 y Odoo 17
- 🎫 Configuración y control de CAI, secuencias y tipos de documentos fiscales
- 📋 Campos adicionales para SAG, OCE, condición de pago y datos fiscales locales
- 📊 Libros de ventas y compras (PDF/XLSX) con filtros por diarios e impuestos
- 🔍 Reportes PT para compras y ventas con cruce contra asientos contables
- 👥 Menús y wizards específicos para usuarios del grupo "Reportes Fiscales de Honduras"
- 🎨 Personalización de colores corporativos en reportes
- 📈 Desglose automático por tasas de ISV (15% y 18%)
- 🔄 Propagación automática de datos SAG desde partners a facturas


Libros Fiscales
---------------
- Libro de Ventas: PDF tradicional, Excel y PT Excel con validaciones
- Libro de Compras: PDF tradicional, Excel y PT Excel con conciliación contable
- Columnas dinámicas derivadas del número de documento
- Filtros configurables por diarios e impuestos
- Totales desglosados por tipo de impuesto

""",
    'depends': [
        'base',
        'account',
        'portal',
        'account_move_name_sequence',
        'res_partner_type_store',
        'l10n_latam_base',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/res_country_state_data.xml',
        'views/l10n_hn_fiscal_locations_view.xml',
        'views/fiscal_document_type_view.xml',
        'views/ir_sequence.xml',
        'views/account_move.xml',
        'views/l10n_hn_cai_wizard_view.xml',
        'views/l10n_hn_cai_view.xml',
        'views/account_journal_view.xml',
        'views/account_config_menu.xml',
        'views/res_config_settings_view.xml',
        'views/res_partner_view.xml',
        'views/sales_report_configuration_view.xml',
        'wizard/sales_report_wizard_view.xml',
        'wizard/purchase_report_wizard_view.xml',
        'views/sales_report_menu.xml',
        'data/l10n_latam_identification_type_data.xml',
        'data/fiscal_document_type_data.xml',
        'data/report_paperformat_data.xml',
        'data/l10n_hn_chart_data.xml',
        'data/account.account.template.csv',
        'data/l10n_hn_chart_post_data.xml',
        'data/account_data.xml',
        'data/account_chart_template_data.xml',
        'report/report_invoice.xml',
        'report/report_sales_book.xml',
        'report/report_purchase_book.xml',
    ],
    "license": "AGPL-3",
    'price': 1000,
    'currency': 'EUR',
    'installable': True,
}
