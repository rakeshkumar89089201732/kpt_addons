{
    'name': 'HR PAN Verification',
    'version': '17.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Verify PAN via external API or offline validation',
    'depends': [
        'hr',
        'hr_contract',
        'hr_contract_extension',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_contract_views.xml',
    ],
    # JavaScript widget removed - using standard char field with Python validation
    # 'assets': {
    #     'web.assets_backend': [
    #         'hr_pan_verification/static/src/js/pan_validator.js',
    #         'hr_pan_verification/static/src/xml/pan_field.xml',
    #         'hr_pan_verification/static/src/scss/pan_field.scss',
    #     ],
    # },
    'installable': True,
    'application': False,
}
