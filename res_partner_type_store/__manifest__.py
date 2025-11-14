{
    'name': 'Partner Store Type',
    'version': '1.0',
    'summary': 'Adds a "Store" type to partners and related fields.',
    'author': 'Allan E. Ramirez Madrid / INTEGRALL',
    'website': 'https://www.integrall.solutions',
    'category': 'Sales',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'security/res_partner_type_store_security.xml',
        'security/ir_rules.xml',
        'views/res_partner_views.xml',
            ],
    'installable': True,
    'application': False,
}
