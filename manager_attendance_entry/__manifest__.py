# -*- coding: utf-8 -*-

{
    'name': 'Manager Attendance Entry',
    'version': '17.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Let managers record attendance for their team with an easy toggle screen',
    'description': """
Manager Attendance Entry
========================
- Provides a dedicated screen for managers to record attendances for their team.
- Automatically uses the current date and time for created attendances.
- Shows a list of the manager’s employees with clear Check In / Check Out actions.
- Integrates with the standard Attendance app (`hr_attendance`).
    """,
    'author': 'KPT',
    'website': 'https://www.kpt.com',
    'depends': ['hr_attendance'],
    'data': [
        'security/ir.model.access.csv',
        'views/manager_attendance_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'manager_attendance_entry/static/src/scss/manager_attendance.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

