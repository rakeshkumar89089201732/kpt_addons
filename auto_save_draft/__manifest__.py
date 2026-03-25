# -*- coding: utf-8 -*-
{
    'name': 'Auto Save Sales Orders',
    'version': '17.0.1.0.0',
    'category': 'Technical',
    'summary': 'Automatic saving of draft Sale Orders',
    'description': """
Auto Save Sales Orders
=======================

Automatically saves draft records for:
- Sale Orders (sale.order)

Features:
- Saves when a customer is first entered to create a valid record
- Saves after 4 minutes of first creating the record
- Then saves every 4 minutes if changes detected
- Only saves when all required fields are filled
- Only operates on draft state records
- Prevents data loss from unsaved work

Search Tags
-----------
auto save sale order | automatic save draft | autosave quotation |
save draft automatically | prevent data loss Odoo | auto save form |
background save sale order | periodic save Odoo | draft order save |
unsaved changes Odoo | lost work prevention | auto save quotation draft |
sale order autosave | quotation auto save | automatic draft save |
save on idle | timed save sale order | auto save every 4 minutes |
smart autosave | silent background save | sale order data loss |
draft save on customer select | required fields save | valid record auto save |
non-intrusive save | zero config autosave | automatic record save |
sale order draft protection | draft quotation save | Odoo autosave module |
save without clicking | background record save | form auto save Odoo |
sale.order auto save | web form autosave | draft protection Odoo |
    """,
    'author': 'ProFast Supply Inc',
    'website': 'https://profast.supply',
    'support': 'it@profast.supply',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'sale_management',
        'stock',
    ],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'auto_save_draft/static/src/js/auto_save_form_controller.js',
        ],
    },
    # No banner shipped in this module
    'installable': True,
    'application': False,
    'auto_install': False,
}
