from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    # Field required by enterprise account_online_synchronization view
    display_alias_fields = fields.Boolean(default=True)
