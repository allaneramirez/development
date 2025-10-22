# -*- coding: utf-8 -*-
# Part of RSM.

{
    "name": "Custom Singature Account Report",
    "author": "RSM BPO",
    "website": "https://www.rsm.com.gt",
    "category": "Accounting",
    "license": "OPL-1",
    "summary": "RSM Custom",
    "version": "17.0",
    "depends": ["account_accountant","account_reports"],
    "data": [
        'security/ir.model.access.csv',
        'views/pdf_export_main.xml'
        # "views/partner_form_view.xml",
    ],
'assets': {
        'web.assets_backend': [
            'sign_account_report/static/src/**/*',
        ],
    },
    "application": True,
    "images": [],
    "auto_install": False,
    "installable": True,
}
