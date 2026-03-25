# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indian TDS System',
    'version': '1.0',
    'sequence': 32,
    'depends': ['hr_contract', 'hr_payroll', 'account'],
    'description': """
        Comprehensive Indian Tax Deducted at Source (TDS) Management System
        
        Features:
        - Complete TDS calculation engine with Indian tax slabs
        - Support for Old and New tax regimes
        - Automatic surcharge and cess calculations
        - Section-wise deduction management (80C, 80D, etc.)
        - TDS certificate generation and tracking
        - Quarterly return preparation (24Q)
        - Challan management and reconciliation
        - Employee self-service portal for tax planning
        - Integration with payroll for automatic deductions
    """,
    "data": [
        'security/ir.model.access.csv',
        'security/tds_security.xml',
        'data/tds_sections_data.xml',
        'data/tax_slabs_data.xml',
        'views/tds_tax_slab_views.xml',
        'views/tds_section_views.xml',
        'views/tds_calculation_views.xml',
        'views/tds_certificate_views.xml',
        'views/tds_challan_views.xml',
        'views/tds_quarterly_return_views.xml',
        'views/hr_employee_tds_views.xml',
        'views/hr_contract_tds_views.xml',
        'views/hr_career_update_views.xml',
        'views/tds_menu_views.xml',
        'reports/tds_certificate_report.xml',
        'reports/tds_quarterly_report.xml',
        'wizard/tds_calculation_wizard_views.xml',
        'wizard/tds_bulk_certificate_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'indian_tds_system/static/src/css/tds_dashboard.css',
            'indian_tds_system/static/src/js/tds_calculator.js',
        ],
    },
    'installable': True,
    'license': 'OEEL-1',
    'auto_install': False,
    'application': True,
    'category': 'Human Resources/Payroll',
}
