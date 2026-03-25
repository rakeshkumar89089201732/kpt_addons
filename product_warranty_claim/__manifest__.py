# -*- coding: utf-8 -*-
{
    'name': 'Product Warranty and Claim',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Warranty Registration, Claims, and Renewals Management',
    'description': """
Product Warranty and Claim Management
=====================================
This module provides comprehensive warranty management for products:

Features:
---------
* Warranty Registration from Sales Orders
* Two Warranty Types: Free and Paid
* Warranty Renewals
* Warranty Claims Management
* Warranty History Tracking
* Product-level Warranty Configuration
* Serial Number Tracking
* Automated Invoice Generation for Paid Warranties
* Warranty Period Calculation (Start Date, End Date, Length)
    """,
    'author': 'KPT',
    'website': 'https://www.kpt.com',
    'depends': ['sale', 'sale_management', 'stock', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'security/product_warranty_security.xml',
        'data/warranty_sequence.xml',
        'views/product_template_views.xml',
        'views/product_warranty_views.xml',
        'views/product_warranty_claim_views.xml',
        'views/product_warranty_renewal_views.xml',
        'views/sale_order_views.xml',
        'views/res_config_settings_views.xml',
        'views/menus.xml',
        'report/warranty_report_templates.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'auto_install': False,
}
