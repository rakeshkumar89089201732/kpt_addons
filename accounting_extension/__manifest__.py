# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Accounting Extension',
    'version': '1.2',
    'sequence': 31,
    'depends': ['account'],
    'description': """
        This module adds an Extension of Accounting.
    """,
    "data": [
        'views/kpt_invoice.xml'
    ],
    'installable': True,
    'license': 'OEEL-1',
    'auto_install': False,
}
