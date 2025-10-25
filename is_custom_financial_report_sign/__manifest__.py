# -*- coding: utf-8 -*-
{
    'name': 'Custom financial report and signature',
    'version': '16.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Add a traditional header and the financial reports, the ability to write a certification and signatures, add a custom style to the PDF and XLSX generation.',
    'author': 'Allan E. Ramirez Madrid / INTEGRALL',

    'depends': [
        'base',
        'account',
        'account_reports',
    ],

    'external_dependencies': {
        'python': [
            'openpyxl',
        ],
    },

    'data': [
        'views/res_config_settings_views.xml',
        'views/res_company_views.xml',
        'views/report_header.xml',
        'views/pdf_export_main.xml',
    ],

    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}