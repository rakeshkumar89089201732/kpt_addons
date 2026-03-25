# -*- coding: utf-8 -*-
{
    'name': "Global Chart of Account Types",
    'summary': """
        Comprehensive Global Chart of Accounts (IFRS, GAAP, Industry Specific)""",
    'description': """
        This module extends the account.account model to add custom account types.
    """,
    'author': "KPT",
    'website': "http://www.kpt.com",
    'category': 'Accounting',
    'version': '17.0.0.1',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/account_type_data.xml',
        'views/global_account_type_views.xml',
        'views/account_account_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
