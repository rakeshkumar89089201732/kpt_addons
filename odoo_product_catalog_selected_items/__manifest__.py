{
    'name': 'Product Catalog Selected Items',
    'version': '17.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'View selected items in product catalog',
    'description': """
        Adds a button to the product catalog view to show a list of all currently selected products.
        Useful for orders with many products to review selection without pagination.
    """,
    'author': 'Community',
    'depends': ['product', 'web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'odoo_product_catalog_selected_items/static/src/xml/selected_items_dialog.xml',
            'odoo_product_catalog_selected_items/static/src/js/selected_items_dialog.js',
            'odoo_product_catalog_selected_items/static/src/js/kanban_controller_patch.js',
            'odoo_product_catalog_selected_items/static/src/js/kanban_record_patch.js',
            'odoo_product_catalog_selected_items/static/src/xml/kanban_controller_patch.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
