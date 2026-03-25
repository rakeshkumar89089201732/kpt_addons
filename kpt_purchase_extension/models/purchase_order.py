from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    kpt_rounding_amount = fields.Monetary(
        string='Rounding',
        compute='_compute_kpt_rounding',
        store=True,
        currency_field='currency_id'
    )
    kpt_amount_total_rounded = fields.Monetary(
        string='Total (Rounded)',
        compute='_compute_kpt_rounding',
        store=True,
        currency_field='currency_id'
    )

    @api.depends('amount_total', 'company_id.purchase_cash_rounding_id')
    def _compute_kpt_rounding(self):
        for order in self:
            rounding = order.company_id.purchase_cash_rounding_id
            if not rounding or not order.currency_id:
                order.kpt_rounding_amount = 0.0
                order.kpt_amount_total_rounded = order.amount_total
                continue

            currency = order.currency_id or order.company_id.currency_id
            base_total = order.amount_total
            rounded_total = rounding.round(base_total)
            diff = currency.round(rounded_total - base_total)
            order.kpt_rounding_amount = diff
            order.kpt_amount_total_rounded = base_total + diff
