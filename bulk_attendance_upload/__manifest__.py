# -*- coding: utf-8 -*-
{
    'name': 'Bulk Attendance Upload',
    'version': '17.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Upload attendance in bulk using Excel/CSV',
    'description': """
Bulk Attendance Upload
======================
- Upload daily attendance logs.
- Upload monthly muster rolls.
- Auto-calculate hours based on shift or default times.
    """,
    'author': 'KPT',
    'website': 'https://www.kpt.com',
    'depends': ['hr', 'hr_attendance', 'resource', 'manager_team_access'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/bulk_attendance_view.xml',
        'views/monthly_attendance_set_wizard_views.xml',
        'views/monthly_attendance_config_wizard_views.xml',
        'views/attendance_dashboard_templates.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'bulk_attendance_upload/static/src/xml/attendance_list_button.xml',
            'bulk_attendance_upload/static/src/xml/attendance_dashboard_action.xml',
            'bulk_attendance_upload/static/src/css/attendance_dashboard_action.css',
            'bulk_attendance_upload/static/src/css/monthly_attendance_list.css',
            'bulk_attendance_upload/static/src/css/monthly_attendance_wizard.css',
            'bulk_attendance_upload/static/src/js/attendance_dashboard.js',
            'bulk_attendance_upload/static/src/js/attendance_dashboard_action.js',
            'bulk_attendance_upload/static/src/js/monthly_attendance_list.js',
            'bulk_attendance_upload/static/src/js/monthly_attendance_list_enhanced.js',
            'bulk_attendance_upload/static/src/js/attendance_list_button.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
