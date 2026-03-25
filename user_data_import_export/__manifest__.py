# -*- coding: utf-8 -*-
{
    'name': 'User Data Import/Export',
    'version': '17.0.1.0.0',
    'category': 'Administration',
    'summary': 'Admin-controlled user data export/import with masked passwords and sample format',
    'description': """
User Data Import/Export
========================
- Admin can set permissions to allow specific users to export/import user data.
- Dedicated security group "User Data Export/Import" - assign to users who may perform user import/export.
- User passwords are masked (********) when exporting user files.
- Sample import format (CSV) is provided for admin users to upload similar files.
- Access rights (groups) are applied automatically when importing user files.
    """,
    'author': 'KPT',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/user_data_import_export_groups.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
