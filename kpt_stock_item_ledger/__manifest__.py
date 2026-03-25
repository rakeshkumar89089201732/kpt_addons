{
    'name': 'KPT Stock Item Ledger',
    'version': '17.0.1.0.1',
    'category': 'Inventory/Reporting',
    'summary': 'Stock item ledger with product selection, date filters, and accounting-style UI',
    'depends': [
        'stock',
        'stock_account',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_item_ledger_product_wizard.xml',
        'views/stock_item_ledger_views.xml',
        'views/stock_item_ledger_report.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}

