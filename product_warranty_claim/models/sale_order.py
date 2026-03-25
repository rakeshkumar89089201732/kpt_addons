# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    warranty_count = fields.Integer(
        string='Warranty Count',
        compute='_compute_warranty_count',
        help='Number of warranties generated from this order'
    )
    
    warranty_ids = fields.One2many(
        'product.warranty',
        'sale_order_id',
        string='Warranties',
        help='Warranties generated from this order'
    )

    def _compute_warranty_count(self):
        for order in self:
            order.warranty_count = len(order.warranty_ids)

    def action_create_warranties(self):
        """Create warranties for products in sale order lines"""
        self.ensure_one()
        if self.state not in ('sale', 'done'):
            raise UserError(_('Warranties can only be created for confirmed or done sale orders.'))
        
        warranty_vals_list = []
        for line in self.order_line:
            if line.product_id and line.product_id.product_tmpl_id.has_warranty:
                # Check if warranty already exists for this line
                existing_warranty = self.env['product.warranty'].search([
                    ('sale_order_line_id', '=', line.id)
                ], limit=1)
                
                if existing_warranty:
                    continue
                
                product_tmpl = line.product_id.product_tmpl_id
                
                # Get serial number from lot if available
                serial_number = False
                lot_id = False
                if line.move_ids:
                    for move in line.move_ids:
                        for move_line in move.move_line_ids:
                            if move_line.lot_id:
                                serial_number = move_line.lot_id.name
                                lot_id = move_line.lot_id.id
                                break
                        if serial_number:
                            break
                
                # Calculate warranty dates
                warranty_start_date = self.date_order.date() if self.date_order else fields.Date.today()
                warranty_period = product_tmpl.warranty_period
                
                # Calculate end date
                start_date = warranty_start_date
                months = warranty_period
                year = start_date.year + (start_date.month + months - 1) // 12
                month = (start_date.month + months - 1) % 12 + 1
                day = min(start_date.day, [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
                warranty_end_date = fields.Date(year, month, day)
                
                warranty_vals = {
                    'partner_id': self.partner_id.id,
                    'product_id': line.product_id.id,
                    'serial_number': serial_number,
                    'lot_id': lot_id,
                    'sale_order_id': self.id,
                    'sale_order_line_id': line.id,
                    'warranty_type': product_tmpl.warranty_type,
                    'warranty_start_date': warranty_start_date,
                    'warranty_end_date': warranty_end_date,
                    'warranty_period': warranty_period,
                    'warranty_price': product_tmpl.warranty_price if product_tmpl.warranty_type == 'paid' else 0.0,
                    'state': 'active',
                }
                warranty_vals_list.append(warranty_vals)
        
        if not warranty_vals_list:
            raise UserError(_('No products with warranty enabled found in this order.'))
        
        warranties = self.env['product.warranty'].create(warranty_vals_list)
        
        # Create invoices for paid warranties if auto-invoice is enabled
        config = self.env['res.config.settings'].sudo().create({})
        if config.auto_create_warranty_invoice:
            for warranty in warranties:
                if warranty.warranty_type == 'paid' and warranty.warranty_price > 0:
                    warranty.action_create_invoice()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Warranties'),
            'res_model': 'product.warranty',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', warranties.ids)],
            'target': 'current',
        }

    def action_view_warranties(self):
        """Open warranties for this order"""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('product_warranty_claim.action_product_warranty')
        action['domain'] = [('sale_order_id', '=', self.id)]
        action['context'] = {'default_sale_order_id': self.id}
        return action


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    warranty_id = fields.Many2one(
        'product.warranty',
        string='Warranty',
        readonly=True,
        help='Warranty generated for this line'
    )
