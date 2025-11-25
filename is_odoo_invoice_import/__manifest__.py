# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------
# Module: odoo_import_invoice
# File: __manifest__.py
# Description:
#     Import invoices, vendor bills, and credit/debit notes directly
#     from Excel (.xls / .xlsx) files into Odoo Accounting.
#
#     Includes support for:
#       ✅ Journal and accounting date from Excel
#       ✅ Product and account mapping
#       ✅ Dynamic validation and error handling
#       ✅ Downloadable Excel template (.xlsx)
#
# Author: Allan E. Ramírez Madrid / INTEGRALL
# License: AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
# ------------------------------------------------------------------------

{
    'name': "Invoice Import from Excel",
    'version': '16.0.2.0',
    'summary': "Import invoices, vendor bills, and credit/debit notes from Excel files (.xls / .xlsx).",
    'description': """
This module provides an advanced wizard to import accounting invoices from Excel spreadsheets.

Main Features:
-------------------------------------------------------
✔ Import Customer Invoices, Vendor Bills, Credit and Debit Notes  
✔ Journal, accounting date, and account codes from Excel  
✔ Option to use product default accounts or Excel-defined accounts  
✔ Automatic currency and tax mapping  
✔ Downloadable example Excel template  
✔ Validation of headers, dates, and numeric values  
✔ Compatible with Odoo 16 Accounting
-------------------------------------------------------
    """,
    'author': "Allan E. Ramírez Madrid / INTEGRALL",
    'maintainer': "Integrall Solutions",
    'website': "https://integrall.solutions",
    'license': 'AGPL-3',
    'category': 'Accounting',
    'depends': [
        'account',
    ],
    'external_dependencies': {
        'python': ['xlrd', 'openpyxl'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_view.xml',
        'wizard/import_excel_wizard.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
