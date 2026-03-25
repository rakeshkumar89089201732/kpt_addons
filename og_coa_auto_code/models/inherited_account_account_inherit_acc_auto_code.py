from odoo import models, fields, api

class AccountAccountInheritAutoCode(models.Model):
    _inherit = "account.account"

    @api.onchange('account_type')
    def _onchange_account_type(self):
        if self.account_type:
            last_rec = self.sudo().search([('account_type', '=', self.account_type)], order='code desc', limit=1)
            if last_rec:
                try:
                    self.code= int(last_rec.code)+1
                except:
                    self.code = ''
            else:
                settings_rec = self.env['account.type.code.settings'].sudo().search([('account_type', '=', self.account_type)], limit=1)
                if settings_rec:
                    self.code = int(settings_rec.code_from)
                else:
                    self.code = ''


