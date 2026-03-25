# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": """Indian - E-waybill Addons""",
    "version": "17.0.1.1.0",
    "category": "Accounting/Localizations/EDI",
    "depends": [
        "l10n_in_edi",
        "l10n_in_edi_ewaybill",
    ],
    "description": """ Indian - E-waybill Addons""",
    "data": [
        'views/account_move.xml',
        'reports/reports.xml',
        'reports/e_waybill_pdf.xml',
        'reports/e_waybill_cancelled.xml',
        'reports/part_a_slip_pdf.xml',
        'reports/part_a_slip_cancelled_pdf.xml'
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
    "license": 'LGPL-3',
}
