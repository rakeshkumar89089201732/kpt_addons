{
    'name': 'Purchase Dynamic Approve',
    'version': '17.0',
    'category': 'Inventory/Purchase',
    'summary': 'Dynamic, Customizable and Flexible Approval Process for Purchase Orders',
    'author': 'INKERP',
    'website': 'https://www.inkerp.com/',
    'depends': ['base', 'purchase'],
    
    'data': [
        'views/purchase_order_teams_views.xml',
        'views/purchase_order_view.xml',
        'security/ir.model.access.csv',
    ],
    
    'images': ['static/description/banner.png'],
    'license': "OPL-1",
    'installable': True,
    'application': True,
    'auto_install': False,
}
