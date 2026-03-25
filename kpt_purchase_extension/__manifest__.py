{
    'name': 'KPT Purchase Extension',
    'version': '17.0.1.0.0',
    'category': 'Purchases',
    'summary': 'Create bills from receipts and auto-create receipts from bills',
    'description': """
        Purchase Extension Module
        =========================
        * Create vendor bills directly from inventory receipts
        * Auto-create receipts when posting vendor bills
        * Bidirectional linking between bills and receipts
        * View linked receipts from bill screen
    """,
    'depends': [
        'purchase',
        'stock',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/apply_tds_wizard_views.xml',
        'views/account_move_views.xml',
        'views/stock_picking_views.xml',
        'views/purchase_order_views.xml',
        'views/res_company_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
