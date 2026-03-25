from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    hr_pan_verification_use_offline = fields.Boolean(
        string='Use Offline Validation (No API)',
        config_parameter='hr_pan_verification.use_offline_validation',
        help='Enable offline PAN validation without external API calls. '
             'This validates PAN format and structure only, without verifying against government database.',
    )
    hr_pan_verification_api_url = fields.Char(
        string='PAN Verification API URL',
        config_parameter='hr_pan_verification.api_url',
    )
    hr_pan_verification_api_host = fields.Char(
        string='PAN Verification API Host',
        config_parameter='hr_pan_verification.api_host',
    )
    hr_pan_verification_api_key = fields.Char(
        string='PAN Verification API Key',
        config_parameter='hr_pan_verification.api_key',
    )
    hr_pan_verification_auto_verify = fields.Boolean(
        string='Auto-Verify PAN on Change',
        config_parameter='hr_pan_verification.auto_verify',
    )
    hr_pan_verification_allow_employee_create = fields.Boolean(
        string='Allow Employee Creation from PAN (Contract)',
        config_parameter='hr_pan_verification.allow_employee_create',
    )
