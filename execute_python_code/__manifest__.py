{
    "name": "Execute Python Code",
    "description": """
        Allow execution of script with User Interface within Odoo
    """,
    "author": "OpenERP SA",
    "version": "0.1",
    "depends": ["base"],
    "data": [
        'security/ir.model.access.csv',
        'view/python_code_view.xml',
    ],
    "installable": True,
    'license': 'LGPL-3',
}
