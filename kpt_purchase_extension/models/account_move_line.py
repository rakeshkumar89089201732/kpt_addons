from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    total_amount_input = fields.Monetary(
        string='Total Amount',
        currency_field='currency_id',
        help='Enter the total tax-exclusive amount for this line. This exact amount will be used as the subtotal.'
    )

    @api.onchange('total_amount_input')
    def _onchange_total_amount_input(self):
        """Auto-calculate unit price from total amount."""
        for line in self:
            if line.total_amount_input and line.quantity and line.quantity > 0:
                # Calculate unit price
                discount_factor = (1 - (line.discount or 0.0) / 100.0)
                if discount_factor > 0:
                    calculated_price = line.total_amount_input / (line.quantity * discount_factor)
                else:
                    calculated_price = line.total_amount_input / line.quantity
                
                line.price_unit = calculated_price

    @api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'currency_id', 'total_amount_input')
    def _compute_totals(self):
        """Override to use total_amount_input when provided."""
        super()._compute_totals()
        for line in self:
            # If total_amount_input is set, use it as the exact price_subtotal
            if line.total_amount_input and line.display_type == 'product':
                line.price_subtotal = line.total_amount_input
                # Recalculate price_total with taxes on the exact subtotal
                if line.tax_ids:
                    taxes_res = line.tax_ids.compute_all(
                        line.total_amount_input,
                        quantity=1,  # Already included in total_amount_input
                        currency=line.currency_id,
                        product=line.product_id,
                        partner=line.partner_id,
                        is_refund=line.is_refund,
                    )
                    line.price_total = taxes_res['total_included']
                else:
                    line.price_total = line.total_amount_input
