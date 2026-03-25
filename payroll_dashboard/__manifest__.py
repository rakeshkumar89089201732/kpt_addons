# -*- coding: utf-8 -*-
{
    'name': 'Payroll Dashboard',
    'version': '17.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Comprehensive payroll dashboard with analytics and insights',
    'description': """
Payroll Dashboard
=================
- Visual dashboard for payroll analytics
- Monthly payroll trends and statistics
- Employee salary insights
- Payslip generation tracking
- Top earners and payroll summaries
    """,
    'author': 'KPT',
    'website': 'https://www.kpt.com',
    'depends': ['hr_payroll', 'hr_contract', 'hr_work_entry_contract_enterprise', 'manager_team_access'],
    'data': [
        'security/ir.model.access.csv',
        'views/payroll_dashboard_templates.xml',
        'views/payroll_dashboard_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'payroll_dashboard/static/src/css/payroll_dashboard.css',
            'payroll_dashboard/static/src/js/payroll_dashboard.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
