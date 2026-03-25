# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Enterprise 17',
    'category': 'Hidden',
    'version': '1.0',
    'description': """
Odoo Enterprise Web Client.
===========================

This module modifies the web addon to provide Enterprise design and responsiveness.
        """,
    'depends': ['web', 'base_setup'],
    'auto_install': False,
    'data': [
        'views/webclient_templates.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            ('after', 'web/static/src/scss/primary_variables.scss', 'enterprise_theme/static/src/**/*.variables.scss'),
            ('before', 'web/static/src/scss/primary_variables.scss', 'enterprise_theme/static/src/scss/primary_variables.scss'),
        ],
        'web._assets_secondary_variables': [
            ('before', 'web/static/src/scss/secondary_variables.scss', 'enterprise_theme/static/src/scss/secondary_variables.scss'),
        ],
        'web._assets_backend_helpers': [
            ('before', 'web/static/src/scss/bootstrap_overridden.scss', 'enterprise_theme/static/src/scss/bootstrap_overridden.scss'),
        ],
        'web.assets_frontend': [
            'enterprise_theme/static/src/webclient/home_menu/home_menu_background.scss', # used by login page
            'enterprise_theme/static/src/webclient/navbar/navbar.scss',
        ],
        'web.assets_backend': [
            'enterprise_theme/static/src/webclient/**/*.scss',
            'enterprise_theme/static/src/views/**/*.scss',

            'enterprise_theme/static/src/core/**/*',
            'enterprise_theme/static/src/webclient/**/*.js',
            'enterprise_theme/static/src/webclient/**/*.xml',
            'enterprise_theme/static/src/views/**/*.js',
            'enterprise_theme/static/src/views/**/*.xml',

            # Don't include dark mode files in light mode
            ('remove', 'enterprise_theme/static/src/**/*.dark.scss'),
        ],
        'web.assets_web': [
            # Replace web's main.js so we load our WebClientEnterprise (works without web_enterprise)
            ('replace', 'web/static/src/main.js', 'enterprise_theme/static/src/main.js'),
        ],
        # ========= Dark Mode =========
        # Define a custom bundle for dark mode variables to avoid collision
        # with web_enterprise's "web.dark_mode_variables" bundle.
        "enterprise_theme.dark_mode_variables": [
            # web._assets_primary_variables
            ('before', 'enterprise_theme/static/src/scss/primary_variables.scss', 'enterprise_theme/static/src/scss/primary_variables.dark.scss'),
            ('before', 'enterprise_theme/static/src/**/*.variables.scss', 'enterprise_theme/static/src/**/*.variables.dark.scss'),
            # web._assets_secondary_variables
            ('before', 'enterprise_theme/static/src/scss/secondary_variables.scss', 'enterprise_theme/static/src/scss/secondary_variables.dark.scss'),
        ],
        "web.assets_web_dark": [
            # ('include', 'web.dark_mode_variables'),
            # Replaced include to avoid pulling assets from web_enterprise's
            # bundle when that addon is not installed.
            ('include', 'enterprise_theme.dark_mode_variables'),
            # web._assets_backend_helpers
            ('before', 'enterprise_theme/static/src/scss/bootstrap_overridden.scss', 'enterprise_theme/static/src/scss/bootstrap_overridden.dark.scss'),
            ('after', 'web/static/lib/bootstrap/scss/_functions.scss', 'enterprise_theme/static/src/scss/bs_functions_overridden.dark.scss'),
            # assets_backend
            'enterprise_theme/static/src/**/*.dark.scss',
        ],
    },
    'license': 'LGPL-3',
}
