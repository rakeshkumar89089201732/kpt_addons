# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'HR Contract Extension',
    'version': '1.2',
    'sequence': 31,
    'depends': ['hr_contract', 'hr_work_entry_contract', 'hr_payroll'],
    'description': """
        This module adds an Extension of hr contract.
    """,
    "data": [
        'security/ir.model.access.csv',
        'data/action_tds_challan.xml',
        'data/salary_attachment_allowance_types.xml',
        'views/tax_slab.xml',
        'views/tds_challan.xml',
        'views/hr_contract.xml',
        'views/res_company.xml',
        'views/tax_scheme.xml',
        'views/hr_tds.xml',
        'views/hr_tds_accordion.xml',
        'views/tds_salary_rule.xml',
        'views/tds_engine_payslip.xml',
        'views/hr_payslip.xml',
        'views/hr_employee.xml',
        'views/hr_salary_attachment_views.xml',
        'reports/tds_report.xml',
        'reports/contract_forms_report.xml',
        'wizard/contract_renewal_wizard_view.xml',
        'wizard/salary_sheet_report_wizard_view.xml',
        'wizard/employee_salary_sheet_wizard_view.xml',
        'wizard/tds_return_xlsx_wizard_view.xml',
        'wizard/tds_24q_template_xlsx_wizard_view.xml',
        'wizard/tds_regime_comparison_wizard_view.xml',
        'wizard/tds_challan_upload_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_contract_extension/static/src/css/tds_accordion.css',
            'hr_contract_extension/static/src/js/tds_accordion.js',
        ],
    },
    'installable': True,
    'license': 'OEEL-1',
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
