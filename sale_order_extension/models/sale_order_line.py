from odoo import models, fields, api
from odoo.tools import float_compare
from odoo.fields import Command

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    pricelist_item = fields.Many2one('product.pricelist.item', string='Price List Item')
    price_unit = fields.Float(
        string="Unit Price",
        compute='_compute_price_unit',
        digits='Product Price',
        store=True, readonly=False, required=True, precompute=True)


    @api.onchange('pricelist_item')
    def _onchange_pricelist_item(self):
        if self.pricelist_item:
            self.price_unit = self.pricelist_item.fixed_price

    @api.depends('display_type', 'product_id', 'product_packaging_qty')
    def _compute_product_uom_qty(self):
        for line in self:
            if line.display_type:
                line.product_uom_qty = 0.0
                continue

            if not line.product_packaging_id:
                continue


    @api.depends('product_packaging_id', 'product_uom', 'product_uom_qty')
    def _compute_product_packaging_qty(self):
        for line in self:
            if not line.product_packaging_id:
                continue


    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_price_unit(self):
        for line in self:
            # check if there is already invoiced amount. if so, the price shouldn't change as it might have been
            # manually edited
            if line.qty_invoiced > 0 or (line.product_id.expense_policy == 'cost' and line.is_expense):
                continue
            if not line.product_uom or not line.product_id:
                line.price_unit = 0.0
            else:
                line.price_unit = line.product_id.list_price if not line.price_unit else line.price_unit

    def _prepare_invoice_line(self, **optional_values):
        """Prepare the values to create the new invoice line for a sales order line.

        :param optional_values: any parameter that should be added to the returned invoice line
        :rtype: dict
        """
        self.ensure_one()
        res = {
            'display_type': self.display_type or 'product',
            'sequence': self.sequence,
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'quantity': self.qty_to_invoice,
            'discount': self.discount,
            'price_unit': self.price_unit,
            'tax_ids': [Command.set(self.tax_id.ids)],
            'sale_line_ids': [Command.link(self.id)],
            'is_downpayment': self.is_downpayment,
            'product_packaging_id': self.product_packaging_id.id,
            'product_packaging_qty': self.product_packaging_qty
        }
        self._set_analytic_distribution(res, **optional_values)
        if optional_values:
            res.update(optional_values)
        if self.display_type:
            res['account_id'] = False
        return res