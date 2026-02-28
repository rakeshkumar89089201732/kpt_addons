from odoo import models, api, fields,_

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mastergst_username = fields.Char(string='Username', related="company_id.mastergst_username", readonly=False)
    mastergst_password = fields.Char(string='Password', related="company_id.mastergst_password", readonly=False)
    mastergst_client_id = fields.Char(string='Client ID', related="company_id.mastergst_client_id", readonly=False)
    mastergst_client_secret = fields.Char(string='Client Secret', related="company_id.mastergst_client_secret", readonly=False)
    ip_address = fields.Char(string='IP Address', related="company_id.ip_address", readonly=False)

    def mastergst_edi_test(self):
        self.l10n_in_check_gst_number()
        response = self.env["mastergst.edi"].mastergst_edi_authenticate(self.company_id)

        # Return the notification from the response directly
        if response and "notification" in response:
            return response["notification"]

        # Fallback error if no proper response was returned
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Authentication Failed"),
                'type': 'danger',
                'message': _("Authentication Failed. Please check the credentials details"),
                'sticky': False,
            },
        }


















