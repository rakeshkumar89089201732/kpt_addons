# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": """Mastergst Addons""",
    "version": "17.0.1.1.0",
    "icon": "/l10n_in/static/description/icon.png",
    "category": "Accounting/Localizations/EDI",
    "depends": ['base','account','l10n_in_edi_ewaybill','eway_addons'],
    'author': 'sabari',
    "description": """
Indian - E-waybill Addons
====================================
To submit E-waybill through API to the government.
We use "Tera Software Limited" as GSP
1. Multi Vehicle 
2. Part - B
    """,
    "data": [
        "security/ir.model.access.csv",
        "views/res_configuration.xml",
        "views/partb.xml",
        "views/initiate_multivehicle.xml",
        "views/add_multivehicle.xml",
        "views/change_vehicle.xml",
        "views/account_move.xml",
        "reports/reports.xml",
        "reports/part_b.xml",
        "reports/cancel_part_b.xml",
        "reports/multivehicle.xml",
        "reports/cancel_multivehicle.xml"
          ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
