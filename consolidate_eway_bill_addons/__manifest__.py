{
    "name": "Consolidate E-Way Bill",
    "version": "17.0.1.1.0",
    "author": "Sabari",
    "depends": ['base', 'mail', 'account', 'l10n_in_edi_ewaybill', 'mastergst_addons'],
    "category": "Accounting/Localizations/EDI",
    "data": [
        "security/ir.model.access.csv",
        "views/get_ewaybill.xml",
        "views/get_ewaybill_products.xml",
        "views/get_ewaybill_vehicles.xml",
        "reports/reports.xml",
        "reports/active_ewaybill_pdf.xml",
        "reports/canclled_ewaybill_pdf.xml"
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}