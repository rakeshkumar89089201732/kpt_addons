# -*- coding: utf-8 -*-
{
    'name': 'Employee Entry and Exit',
    'version': '17.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Employee Offer Letter, Entry and Exit Management',
    'description': """
Employee Entry and Exit Management
===================================
This module provides comprehensive employee lifecycle management:

Features:
---------
* Employee Offer Letter Management
* Offer Letter Generation (PDF)
* Automatic Employee Creation on Offer Acceptance
* Automatic Contract Creation
* Job Position Management
* Salary and Allowances Configuration
* Offer Workflow: Draft → Sent → Accepted/Rejected
* Integration with Payroll System
    """,
    'author': 'KPT',
    'website': 'https://www.kpt.com',
    'depends': [
        'hr',
        'hr_contract',
        'hr_recruitment',
        'hr_work_entry_contract_enterprise',
        'base',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/employee_entry_exit_security.xml',
        'data/offer_sequence.xml',
        'views/offer_letter_template_views.xml',
        'views/employee_offer_views.xml',
        'views/hr_employee_views.xml',
        'views/menus.xml',
        'views/menu_order_override.xml',
        'report/offer_letter_report.xml',
        'report/offer_letter_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'employee_entry_exit/static/src/css/employee_entry_exit.css',
            'employee_entry_exit/static/src/css/variable_autocomplete.css',
            'employee_entry_exit/static/src/js/html_field_autocomplete.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
