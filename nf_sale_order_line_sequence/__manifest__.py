# -*- coding: utf-8 -*-
# Copyright (C) 2021-Today: Part of NextFlowIT.
# @author:  Part of NextFlowIT.

{
    'name': 'KPT saleorder sequence',
    'summary': """
Sales order line sequence number in order line with sequence number report purchase order line sequence sale order line sequence purchase agreement order line report sales stock order line sequence sale order line number order line sequence number report sale order line number purchase order line number sale number purchase number sale sequence purchase sequence order line sequence order line number
    """,
    'post_init_hook': 'post_init_hook',
    'description': """
    The Display Sale Order Line Numbers module enhances Odoo's usability by automatically adding line numbers to Sales Orders

This small but powerful improvement helps users quickly identify, reference, and organize order lines - especially useful when handling large or complex orders.
    """,
    'version': '17.0.0.1',
    'category': 'Extra Tools',
    'author': 'NextFlowIT',
    'company': 'NextFlow Technology',
    'maintainer': 'NextFlow Technology',
    'website': 'nextflow.in',
    'depends':['sale_management'],
    'data':[
        'report/nf_sale_order_line_report.xml',
        'views/nf_sale_order_line_view.xml',
    ],
    'images': ['static/description/background.gif'],
    'license': "OPL-1",
    'installable': True,
    'auto_install': False,
    'application': False,
    "price": 0.00,
    "currency": "USD"
}
