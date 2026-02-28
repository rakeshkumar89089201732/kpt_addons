from odoo import models, fields, api

class StockMove(models.Model):
    _inherit = 'stock.move'

    price_unit = fields.Float("Unit Price")
    tax_id = fields.Many2many('account.tax', 'stock_move_taxes_rel', string='Taxes')
    price_subtotal = fields.Monetary(
        string="Subtotal",
        compute='_compute_amount',
        store=True, )
    price_tax = fields.Float(
        string="Total Tax",
        compute='_compute_amount',
        store=True, )
    price_total = fields.Monetary(
        string="Total",
        compute='_compute_amount',
        store=True, )
    price_reduce_taxexcl = fields.Monetary(
        string="Price Reduce Tax excl",
        compute='_compute_price_reduce_taxexcl',
        store=True, )
    price_reduce_taxinc = fields.Monetary(
        string="Price Reduce Tax incl",
        compute='_compute_price_reduce_taxinc',
        store=True, )
    currency_id = fields.Many2one(
        related='picking_id.currency_id',
        depends=['picking_id.currency_id'],
        store=True, )

    discount = fields.Float(
        string="Discount (%)",
        digits='Discount',
        store=True, readonly=False)

    pricelist_item = fields.Many2one('product.pricelist.item', string='Price List Item')





    @api.onchange('pricelist_item')
    def _onchange_pricelist_item(self):
        if self.pricelist_item:
            self.price_unit = self.pricelist_item.fixed_price



    # @api.depends('product_id', 'product_uom', 'product_uom_qty')
    # def _compute_discount(self):
    #     for line in self:
    #         # if line.product_id:
    #         line.discount = 0.0
    #
    #         # line = line.with_company(line.company_id)
    #         # pricelist_price = line._get_pricelist_price()
    #         #     base_price = line._get_pricelist_price_before_discount()
    #         #
    #         # if base_price != 0:  # Avoid division by zero-+
    #         #     discount = (base_price - pricelist_price) / base_price * 100
    #         #     if (discount > 0 and base_price > 0) or (discount < 0 and base_price < 0):
    #         #         # only show negative discounts if price is negative
    #         #         # otherwise it's a surcharge which shouldn't be shown to the customer
    #         #         line.discount = discount

    @api.depends('quantity', 'price_unit', 'tax_id', 'discount', 'product_uom_qty')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            tax_results = self.env['account.tax'].with_company(line.company_id)._compute_taxes([
                line._convert_to_tax_base_line_dict()
            ])
            totals = list(tax_results['totals'].values())[0]
            amount_untaxed = totals['amount_untaxed']
            amount_tax = totals['amount_tax']

            line.update({
                'price_subtotal': amount_untaxed,
                'price_tax': amount_tax,
                'price_total': amount_untaxed + amount_tax,
            })

    @api.depends('price_subtotal', 'quantity', 'product_uom_qty')
    def _compute_price_reduce_taxexcl(self):
        for line in self:
            line.price_reduce_taxexcl = line.price_subtotal / (line.quantity or line.product_uom_qty) if line.quantity or line.product_uom_qty else 0.0

    @api.depends('price_total', 'quantity', 'product_uom_qty')
    def _compute_price_reduce_taxinc(self):
        for line in self:
            line.price_reduce_taxinc = line.price_total / (line.quantity or line.product_uom_qty) if line.quantity or line.product_uom_qty else 0.0


    def _convert_to_tax_base_line_dict(self, **kwargs):
        """ Convert the current record to a dictionary in picking to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.picking_id.partner_id,
            currency=self.picking_id.currency_id,
            product=self.product_id,
            taxes=self.tax_id,
            price_unit=self.price_unit,
            quantity=self.quantity or self.product_uom_qty,
            discount=self.discount,
            price_subtotal=self.price_subtotal,
            **kwargs,
        )

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for move in res:
            if move.sale_line_id:
                move.write({'price_unit':  move.sale_line_id.price_unit, 'tax_id': move.sale_line_id.tax_id, 'discount': move.sale_line_id.discount, 'pricelist_item': move.sale_line_id.pricelist_item})
            if move.purchase_line_id:
                move.write({'price_unit': move.purchase_line_id.price_unit, 'tax_id': move.purchase_line_id.taxes_id, 'discount': move.purchase_line_id.discount})
        return res
