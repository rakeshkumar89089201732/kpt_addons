{
    'name': 'Lock Orders',
    'version': '17.0.1.0.0',
    'category': 'Productivity',
    'summary': 'Strictly lock Sale, Purchase, Repair, and Inventory orders in finalized states',
    'description': """
        This module enforces strict read-only access (locking) on:
        - Sale Orders (Locked/Done)
        - Purchase Orders (Purchase/Done)
        - Repair Orders (Done)
        - Stock Pickings (Done)
        
        It provides a privileged 'Revoke to Draft' button, restricted to the 'Unlock / Revoke Orders' group, 
        allowing authorized users to reset orders for correction.
    """,
    'author': 'Community',
    'depends': ['sale', 'purchase', 'stock', 'repair'],
    'data': [
        'security/security.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/repair_order_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
