{
    'name': 'Odoo UI Enhancements',
    'version': '17.0.1.0.0',
    'category': 'Hidden',
    'summary': 'Generic UI enhancements for better tree view display and field alignment',
    'description': """
        Odoo UI Enhancements
        ====================
        Generic UI improvements for Odoo including:
        - Tree view column header alignment and display
        - Field label visibility and truncation fixes
        - Consistent spacing and padding across list views
        - Better readability and responsive design
        - Works with any Odoo module or custom development
    """,
    'author': 'Community',
    'website': '',
    'depends': ['web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'odoo_ui_enhancements/static/src/scss/tree_view_fixes.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
