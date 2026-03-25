{
    'name': 'KPT Pricelist Update',
    'version': '17.0.1.0.5',
    'summary': 'Wizard to create updated pricelists based on categories and formulas',
    'category': 'Sales',
    'author': 'KPT',
    'depends': ['sale', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/kpt_pricelist_update_view.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
