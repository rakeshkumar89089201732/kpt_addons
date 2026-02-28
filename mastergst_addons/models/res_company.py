from odoo import models, api, fields, _

class ResCompany(models.Model):
    _inherit = 'res.company'

    mastergst_username = fields.Char(string='Username', groups="base.group_system")
    mastergst_password = fields.Char(string='Password', groups="base.group_system")
    mastergst_client_id = fields.Char(string='Client ID', groups="base.group_system")
    mastergst_client_secret = fields.Char(string='Client Secret', groups="base.group_system")
    ip_address = fields.Char(string='IP Address')
