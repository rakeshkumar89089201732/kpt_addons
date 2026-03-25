# -*- coding: utf-8 -*-
{
    'name': 'Sale Invoice Policy Fix',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Fix for invoice_policy field compatibility',
    'description': """
        Adds compatibility field invoice_policy to res.config.settings
        to fix views that reference the old field name.
    """,
    'author': 'KPT',
    'depends': ['sale'],
    'data': [],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
