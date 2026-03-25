# -*- coding: utf-8 -*-
{
    'name': 'KPT Multi-Currency Performa Invoice',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Multi-currency support for sale orders with automatic currency selection based on customer',
    'description': """
        Multi-Currency Performa Invoice
        ================================
        * Automatic currency selection based on customer's currency
        * Manual currency change option in sale order/quotation
        * Currency field visible in sale order form view
        * Automatic price recalculation when currency changes
    """,
    'author': 'KPT',
    'website': 'https://www.kpt.com',
    'depends': ['sale_management', 'account'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
