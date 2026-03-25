# -*- coding: utf-8 -*-
{
    'name': 'Inventory Dashboard',
    'version': '17.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Comprehensive Inventory Dashboard with Real-time Metrics',
    'description': """
Inventory Dashboard
===================
This module provides a comprehensive dashboard for inventory management:

Features:
---------
* Real-time Stock Levels Overview
* Low Stock Alerts
* Recent Stock Movements
* Top Products by Quantity
* Warehouse Overview
* Stock Valuation Summary
* Product Categories Analysis
* Stock Aging Analysis
* Quick Actions for Common Tasks
    """,
    'author': 'KPT',
    'website': 'https://www.kpt.com',
    'depends': ['stock', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/inventory_dashboard_templates.xml',
        'views/inventory_dashboard_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'inventory_dashboard/static/src/xml/inventory_dashboard_action.xml',
            'inventory_dashboard/static/src/css/inventory_dashboard.css',
            'inventory_dashboard/static/src/css/inventory_dashboard_action.css',
            'inventory_dashboard/static/src/js/inventory_dashboard_action.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
