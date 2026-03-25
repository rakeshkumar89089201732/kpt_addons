# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'KPT Packaging Extension',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Extended packaging information with weight per piece and pieces per packaging',
    'description': """
        KPT Packaging Extension
        =======================
        Extends product packaging to include:
        - Weight per piece (Wt./Pcs)
        - Pieces per packaging (PCS/Bag)
        - Packaging weight (empty packaging weight)
        - Calculated average weight per packaging (AVG Wt./Bag)
        
        This module is designed for products like couplings where precise
        weight tracking per piece and per packaging unit is required.
    """,
    'author': 'KPT',
    'website': 'https://www.kpt.com',
    'depends': ['product', 'stock'],
    'data': [
        'views/product_packaging_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
