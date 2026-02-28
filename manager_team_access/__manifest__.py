# -*- coding: utf-8 -*-
{
    'name': 'Manager Team Access',
    'version': '17.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Restrict managers to see only their own and their team employees data',
    'description': """
Manager Team Access
==================
- Gives managers access to their own data and their direct/indirect subordinates only.
- Configurable per model: employees, contracts, contacts, attendance, leaves, expenses.
- Dynamic: add or remove models and rules from Settings.
- Based on hr.employee parent_id (manager) hierarchy.
    """,
    'author': 'KPT',
    'license': 'LGPL-3',
    'depends': [
        'hr',
        'hr_contract',
        'hr_attendance',
        'hr_holidays',
        'hr_expense',
        'hr_payroll',
    ],
    'data': [
        'security/manager_team_access_groups.xml',
        'security/ir.model.access.csv',
        'security/manager_team_access_ir_rule.xml',
        'data/manager_team_access_rule_data.xml',
        'views/manager_team_access_rule_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
