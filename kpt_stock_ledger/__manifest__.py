{
    'name': 'KPT Stock Ledger',
    'version': '17.0.1.0.0',
    'summary': 'Stock Ledger Report with Inwards/Outwards and Closing Balance',
    'description': """
        Stock Ledger Module
        ===================
        - Product-wise stock ledger with date range
        - Shows Opening Balance, Inwards, Outwards, and Closing Balance
        - Tracks quantity and value for each transaction
        - Supports all voucher types (Sales, Purchase, Stock Journal, etc.)
        - Wizard-based report generation
    """,
    'category': 'Inventory',
    'author': 'KPT',
    'license': 'LGPL-3',
    'depends': [
        'stock',
        'stock_account',
        'sale_stock',
        'purchase_stock',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/stock_ledger_wizard_views.xml',
        'views/stock_ledger_views.xml',
        'views/stock_ledger_report_views.xml',
        'report/stock_ledger_report_template.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
