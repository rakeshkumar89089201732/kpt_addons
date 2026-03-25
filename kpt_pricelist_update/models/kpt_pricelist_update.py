from odoo import models, fields, api, _
from odoo.exceptions import UserError

class KptPricelistUpdate(models.TransientModel):
    _name = 'kpt.pricelist.update.wizard'
    _description = 'KPT Pricelist Update Wizard'

    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    category_ids = fields.Many2many('product.category', string='Product Categories', required=True)
    
    source_type = fields.Selection([
        ('list_price', 'Sales Price'),
        ('standard_price', 'Cost'),
        ('pricelist', 'Other Pricelist')
    ], string='Based On', default='pricelist', required=True)
    
    base_pricelist_id = fields.Many2one('product.pricelist', string='Base Pricelist')
    
    update_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount')
    ], string='Update Type', default='percentage', required=True)
    
    operation = fields.Selection([
        ('increase', 'Increase'),
        ('decrease', 'Decrease')
    ], string='Operation', default='increase', required=True)
    
    value = fields.Float(string='Value', required=True)
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        return res

    @api.onchange('category_ids')
    def _onchange_category_ids(self):
        if not self.category_ids:
            return {'domain': {'base_pricelist_id': []}}
            
        # Find pricelists that have items for these categories or products in these categories
        domain = [
            '|', '|',
            ('categ_id', 'child_of', self.category_ids.ids),
            ('product_id.categ_id', 'child_of', self.category_ids.ids),
            ('product_tmpl_id.categ_id', 'child_of', self.category_ids.ids)
        ]
        items = self.env['product.pricelist.item'].search(domain)
        pricelist_ids = items.mapped('pricelist_id').ids
        
        return {'domain': {'base_pricelist_id': [('id', 'in', pricelist_ids)]}}

    def action_update_pricelist(self):
        self.ensure_one()
        
        # Determine base name
        base_name = ''
        if self.source_type == 'pricelist' and self.base_pricelist_id:
            base_name = self.base_pricelist_id.name
        elif self.source_type == 'list_price':
            base_name = 'Sales Price'
        elif self.source_type == 'standard_price':
            base_name = 'Cost'
            
        new_name = f"{self.date} ({base_name})"
        
        # Create new pricelist
        vals = {
            'name': new_name,
            'company_id': self.env.company.id,
        }
        if self.source_type == 'pricelist' and self.base_pricelist_id and self.base_pricelist_id.currency_id:
            vals['currency_id'] = self.base_pricelist_id.currency_id.id

        new_pricelist = self.env['product.pricelist'].create(vals)
        
        PricelistItem = self.env['product.pricelist.item']
        
        # Find products in selected categories
        products = self.env['product.product'].search([('categ_id', 'child_of', self.category_ids.ids)])
        
        if not products:
            raise UserError(_("No products found in the selected categories. Please select categories that contain products."))
            
        item_list = []
        for product in products:
            base_price = 0.0
            if self.source_type == 'pricelist' and self.base_pricelist_id:
                # Calculate based on 1 unit
                base_price = self.base_pricelist_id._get_product_price(product, quantity=1.0, date=self.date)
            elif self.source_type == 'list_price':
                base_price = product.lst_price
            elif self.source_type == 'standard_price':
                base_price = product.standard_price
            
            if base_price == 0.0:
                 raise UserError(_(f"Base price for product '{product.name}' is 0.0. Please check the source price or remove this product from the category."))

            new_price = 0.0
            if self.update_type == 'percentage':
                if self.operation == 'increase':
                    new_price = base_price * (1 + (self.value / 100))
                else:
                    new_price = base_price * (1 - (self.value / 100))
            else:
                if self.operation == 'increase':
                    new_price = base_price + self.value
                else:
                    new_price = base_price - self.value
            
            # Apply currency rounding if currency exists
            if new_pricelist.currency_id:
                new_price = new_pricelist.currency_id.round(new_price)
            
            item_list.append({
                'pricelist_id': new_pricelist.id,
                'applied_on': '0_product_variant',
                'product_id': product.id,
                'compute_price': 'fixed',
                'fixed_price': new_price,
                'min_quantity': 0,
                'date_start': fields.Datetime.to_datetime(self.date),
            })
            
        if item_list:
            PricelistItem.create(item_list)
            
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.pricelist',
            'res_id': new_pricelist.id,
            'view_mode': 'form',
            'target': 'current',
        }
