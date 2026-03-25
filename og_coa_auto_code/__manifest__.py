# -*- coding: utf-8 -*-
################################################################################
#
#    Ogroni Informatix Limited
#
#    Copyright (C) 2024-TODAY Ogroni Informatix Limited(<https://www.ogroni.com/>).
#    Author: Billal (billal.hossain@ogroni.com)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
{
    'name': 'Odoo17 Chart of Accounts Auto Coding',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': "Odoo17 Chart of Accounts Auto Coding–"
               "Enterprise Edition",
    'description': "This module creates options for Automatic code of Accounting "
                   "chart of accounts in odoo17 Enterprise edition",
    'author': 'Ogroni Informatix Limited',
    'company': 'Ogroni Informatix Limited',
    'maintainer': 'Ogroni Informatix Limited',
    'website': "https://www.ogroni.com",
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_type_code_settings_views.xml',
        'views/inherited_account_account_inherit_acc_auto_code_views.xml',
    ],

    'images': ['static/description/banner.png'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
