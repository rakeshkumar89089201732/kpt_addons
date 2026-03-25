# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        tracking=True,
        help="Currency used for this sale order. Will be set automatically based on customer's currency."
    )

    @api.onchange('partner_id')
    def _onchange_partner_id_currency(self):
        if self.partner_id and self.partner_id.property_product_pricelist:
            pricelist = self.partner_id.property_product_pricelist
            if pricelist.currency_id:
                self.currency_id = pricelist.currency_id
        elif self.partner_id and hasattr(self.partner_id, 'currency_id') and self.partner_id.currency_id:
            self.currency_id = self.partner_id.currency_id
        else:
            self.currency_id = self.env.company.currency_id

    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        if not self.currency_id:
            return
        
        if self.pricelist_id and self.pricelist_id.currency_id != self.currency_id:
            pricelist_with_currency = self.env['product.pricelist'].search([
                ('currency_id', '=', self.currency_id.id),
                ('company_id', 'in', [False, self.company_id.id])
            ], limit=1)
            
            if pricelist_with_currency:
                self.pricelist_id = pricelist_with_currency
            
        if self.order_line:
            self.order_line._compute_tax_id()

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        if self.currency_id:
            invoice_vals['currency_id'] = self.currency_id.id
        return invoice_vals
