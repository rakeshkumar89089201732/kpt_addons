# -*- coding: utf-8 -*-
{
    'name': 'HR Attendance Approval',
    'version': '17.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Dynamic Multi-Level Attendance Approval System',
    'description': """
        HR Attendance Approval Module
        ==============================
        Features:
        - Daily check-in and check-out for employees
        - Manager approval for attendance (daily)
        - Bulk approval and individual approval
        - Multi-level approval configuration
        - Access control based on hierarchy (Manager, Super Manager, Administrator)
    """,
    'author': 'KPT',
    'website': '',
    'depends': [
        'base',
        'hr',
        'hr_attendance',
    ],
    'data': [
        'security/hr_attendance_approval_security.xml',
        'security/ir.model.access.csv',
        'data/attendance_approval_data.xml',
        'wizard/attendance_bulk_approve_wizard_views.xml',
        'wizard/monthly_attendance_register_wizard_views.xml',
        'views/hr_attendance_views.xml',
        'views/hr_attendance_action_override.xml',
        'views/hr_attendance_approval_config_views.xml',
        'views/hr_attendance_approval_views.xml',
        'views/hr_employee_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
