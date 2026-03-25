# -*- coding: utf-8 -*-
{
    'name': 'Keyboard Shortcuts Configuration',
    'version': '17.0.1.0.0',
    'category': 'Productivity',
    'summary': 'Configure custom keyboard shortcuts for individual users and globally',
    'description': """
        Keyboard Shortcuts Configuration Module
        ========================================
        
        Features:
        ---------
        * Configure keyboard shortcuts at user level or globally
        * Support for various actions: next field, new line, save, create, etc.
        * Visual shortcut key recorder
        * Import/Export shortcut configurations
        * Predefined shortcut templates
        * Support for modifier keys (Ctrl, Alt, Shift, Meta)
        * Context-aware shortcuts (form, list, kanban views)
        * Enable/disable shortcuts individually
        * Conflict detection and resolution
        
        Common Use Cases:
        ----------------
        * Enter key for next field navigation
        * Ctrl+Enter for new line in text fields
        * Custom save shortcuts
        * Quick record creation
        * Navigation shortcuts
    """,
    'author': 'KPT',
    'website': 'https://www.kpt.com',
    'depends': ['base', 'web'],
    'data': [
        'security/shortcut_security.xml',
        'security/ir.model.access.csv',
        'data/shortcut_action_data.xml',
        'data/default_shortcuts_data.xml',
        'wizard/shortcut_import_export_views.xml',
        'views/keyboard_shortcut_views.xml',
        'views/shortcut_action_views.xml',
        'views/res_users_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'keyboard_shortcuts_config/static/src/js/shortcut_manager.js',
            'keyboard_shortcuts_config/static/src/js/shortcut_recorder.js',
            'keyboard_shortcuts_config/static/src/xml/shortcut_recorder.xml',
            'keyboard_shortcuts_config/static/src/css/shortcut_styles.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
