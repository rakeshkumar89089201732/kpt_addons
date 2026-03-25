# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": """Account Edi Addons""",
    "version": "17.0.1.1.0",
    "category": "Accounting/Localizations/EDI",
    "depends": [
        "account_edi",
        "l10n_in",
        "iap",
        "account",
    ],
    "description": """ Account Edi Addons""",
    "data": [
        'views/account_move.xml',
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
    "license": 'LGPL-3',
}
