# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": """Indian - E-invoicing Addons""",
    "version": "17.0.1.1.0",
    "category": "Accounting/Localizations/EDI",
    "depends": [
        "account_edi",
        "l10n_in",
        "iap",
    ],
    "description": """ Indian - E-invoicing Addons""",
    "data": [
        'views/account_move.xml',
        'reports/reports.xml',
        'reports/nano_einvoice.xml',
        'reports/nano_einvoice_cancelled.xml',
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
    "license": 'LGPL-3',
}
