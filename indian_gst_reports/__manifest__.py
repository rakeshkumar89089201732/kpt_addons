# -*- coding: utf-8 -*-
{
    'name': "Indian GST Reports by LucidBrainz",
    'summary': """
        Comprehensive GSTR-1, GSTR-2, GSTR-3B, and GSTR-9 Excel Reports""",
    'description': """
        Generates mandatory Indian GST returns in Excel format.
        Features:
        - GSTR-1: Outward Supplies (B2B, B2C, Exports, HSN, etc.)
        - GSTR-2: Inward Supplies
        - GSTR-3B: Monthly Summary
        - GSTR-9: Annual Return
        - Multi-Company & Multi-Currency support
    """,
    'author': "LucidBrainz",
    'website': "https://www.lucidbrainz.com",
    'category': 'Accounting/Reporting',
    'version': '17.0.1.0.0',
    'depends': ['account', 'l10n_in'],
    'data': [
        'security/ir.model.access.csv',
        'views/gst_report_wizard_views.xml',
    ],
    'images': [],
    'license': 'OPL-1',
    'installable': True,
    'application': True,
}
