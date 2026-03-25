# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    warranty_type = fields.Selection([
        ('free', 'Free Warranty'),
        ('paid', 'Paid Warranty'),
    ], string='Warranty Type', default='free', help='Type of warranty for this product')
    
    warranty_period = fields.Integer(
        string='Warranty Period (Months)',
        default=12,
        help='Default warranty period in months'
    )
    
    warranty_price = fields.Float(
        string='Warranty Price',
        default=0.0,
        help='Price for paid warranty (if warranty type is Paid)'
    )
    
    has_warranty = fields.Boolean(
        string='Has Warranty',
        default=True,
        help='Enable warranty for this product'
    )
    
    warranty_count = fields.Integer(
        string='Warranty Count',
        compute='_compute_warranty_count',
        help='Number of warranties registered for this product'
    )

    def _compute_warranty_count(self):
        for product in self:
            product.warranty_count = self.env['product.warranty'].search_count([
                ('product_id.product_tmpl_id', '=', product.id)
            ])

    def action_view_warranties(self):
        """Open warranties for this product"""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('product_warranty_claim.action_product_warranty')
        action['domain'] = [('product_id.product_tmpl_id', '=', self.id)]
        action['context'] = {'default_product_id': self.product_variant_id.id if self.product_variant_count == 1 else False}
        return action
