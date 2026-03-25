{
    'name': 'Sale Order Discount Approval',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'depends': ['base',
        'sale_management',
        'sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/sale_order_discount_approval_odoo_groups.xml',
        'report/sale_order_template.xml',
        'view/res_users_views.xml',
        'view/sale_order_views.xml',
        'view/printing_label.xml'

    ],
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
