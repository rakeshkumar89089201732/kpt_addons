{
    'name': 'Restrict Negative Stock',
    'version': '17.0.1.0.1',
    'category': 'Inventory/Stock',
    'summary': 'Restrict negative stock with configurable exceptions per product, category, or location.',
    'description': """
Restrict Negative Stock for Odoo 17
===================================

This module prevents negative stock for **stockable products** by blocking operations that would result in stock levels below zero.  
It ensures accurate inventory management and allows **flexible configuration** for exceptions.

**Key Features**
----------------
- ✅ Block negative stock for **stockable products**
- ✅ Allow exceptions for:
    * Individual products *(via checkbox)*
    * Product categories *(via checkbox)*
    * Specific stock locations *(via checkbox)*
- ✅ Works with deliveries, pickings, manufacturing orders, and internal transfers
- ✅ Consumable products are **not affected**
- ✅ Simple configuration through Inventory settings

**Usage**
---------
1. Go to **Inventory → Products** → Enable **Allow Negative Stock** on products where exceptions are allowed.
2. Go to **Inventory → Product Categories** → Enable **Allow Negative Stock** for category-level exceptions.
3. Go to **Inventory → Locations** → Enable **Allow Negative Stock** for specific warehouses or locations.

**Compatibility**
-----------------
- Odoo 17 Community ✅
- Odoo 17 Enterprise ✅

    """,
    'author': 'Mudassir Amin',
    'website': 'https://mudassir.odoo',
    'license': 'LGPL-3',
    'depends': ['stock'],
    'data': [
        'views/product_views.xml',
        'views/product_category_views.xml',
        'views/stock_location_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'price': 0.0,
    'currency': 'USD',
}
