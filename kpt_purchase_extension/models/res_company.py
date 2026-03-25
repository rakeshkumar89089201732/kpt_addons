from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    purchase_cash_rounding_id = fields.Many2one(
        'account.cash.rounding',
        string='Purchase Cash Rounding',
        help='Default cash rounding applied to vendor bills and used for PO round-off display.'
    )
