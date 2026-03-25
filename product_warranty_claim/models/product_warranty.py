# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ProductWarranty(models.Model):
    _name = 'product.warranty'
    _description = 'Product Warranty'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'warranty_start_date desc, name desc'

    name = fields.Char(
        string='Warranty Number',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _('New'),
        tracking=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
        help='Customer who owns this warranty'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        tracking=True,
        help='Product covered by this warranty'
    )
    
    product_tmpl_id = fields.Many2one(
        'product.template',
        related='product_id.product_tmpl_id',
        string='Product Template',
        store=True,
        readonly=True
    )
    
    serial_number = fields.Char(
        string='Serial Number',
        tracking=True,
        help='Serial number of the product'
    )
    
    lot_id = fields.Many2one(
        'stock.lot',
        string='Lot/Serial Number',
        domain="[('product_id', '=', product_id)]",
        help='Lot/Serial number from inventory'
    )
    
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        readonly=True,
        help='Sale order from which this warranty was generated'
    )
    
    sale_order_line_id = fields.Many2one(
        'sale.order.line',
        string='Sale Order Line',
        readonly=True,
        help='Sale order line from which this warranty was generated'
    )
    
    warranty_type = fields.Selection([
        ('free', 'Free Warranty'),
        ('paid', 'Paid Warranty'),
    ], string='Warranty Type', required=True, default='free', tracking=True)
    
    warranty_start_date = fields.Date(
        string='Warranty Start Date',
        required=True,
        default=fields.Date.today,
        tracking=True,
        help='Date when warranty period starts'
    )
    
    warranty_end_date = fields.Date(
        string='Warranty End Date',
        required=True,
        tracking=True,
        help='Date when warranty period ends'
    )
    
    warranty_period = fields.Integer(
        string='Warranty Period (Months)',
        required=True,
        default=12,
        tracking=True,
        help='Warranty period in months'
    )
    
    warranty_price = fields.Float(
        string='Warranty Price',
        default=0.0,
        tracking=True,
        help='Price paid for warranty (if paid warranty)'
    )
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        readonly=True,
        help='Invoice generated for paid warranty'
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, compute='_compute_state', store=True)
    
    is_expired = fields.Boolean(
        string='Is Expired',
        compute='_compute_state',
        store=True
    )
    
    days_remaining = fields.Integer(
        string='Days Remaining',
        compute='_compute_state',
        help='Number of days remaining in warranty'
    )
    
    claim_count = fields.Integer(
        string='Claims Count',
        compute='_compute_claim_count',
        help='Number of warranty claims'
    )
    
    renewal_count = fields.Integer(
        string='Renewals Count',
        compute='_compute_renewal_count',
        help='Number of warranty renewals'
    )
    
    note = fields.Text(string='Notes')
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )

    @api.depends('warranty_end_date', 'state')
    def _compute_state(self):
        today = fields.Date.today()
        for warranty in self:
            if warranty.state == 'cancelled':
                continue
            if warranty.warranty_end_date and warranty.warranty_end_date < today:
                warranty.state = 'expired'
                warranty.is_expired = True
                warranty.days_remaining = 0
            elif warranty.state == 'draft':
                warranty.is_expired = False
                if warranty.warranty_end_date:
                    delta = warranty.warranty_end_date - today
                    warranty.days_remaining = delta.days if delta.days > 0 else 0
            else:
                warranty.state = 'active'
                warranty.is_expired = False
                if warranty.warranty_end_date:
                    delta = warranty.warranty_end_date - today
                    warranty.days_remaining = delta.days if delta.days > 0 else 0

    def _compute_claim_count(self):
        for warranty in self:
            warranty.claim_count = self.env['product.warranty.claim'].search_count([
                ('warranty_id', '=', warranty.id)
            ])

    def _compute_renewal_count(self):
        for warranty in self:
            warranty.renewal_count = self.env['product.warranty.renewal'].search_count([
                ('warranty_id', '=', warranty.id)
            ])

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('product.warranty') or _('New')
        
        # Calculate warranty end date if not provided
        if 'warranty_start_date' in vals and 'warranty_period' in vals:
            if 'warranty_end_date' not in vals or not vals.get('warranty_end_date'):
                start_date = fields.Date.from_string(vals['warranty_start_date'])
                months = vals['warranty_period']
                # Add months to start date
                year = start_date.year + (start_date.month + months - 1) // 12
                month = (start_date.month + months - 1) % 12 + 1
                day = min(start_date.day, [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
                vals['warranty_end_date'] = fields.Date.to_string(fields.Date(year, month, day))
        
        warranty = super(ProductWarranty, self).create(vals)
        
        # Set state to active if start date is today or past
        if warranty.warranty_start_date <= fields.Date.today():
            warranty.state = 'active'
        
        return warranty

    def write(self, vals):
        # Recalculate warranty end date if period or start date changes
        if 'warranty_start_date' in vals or 'warranty_period' in vals:
            for warranty in self:
                start_date = fields.Date.from_string(vals.get('warranty_start_date', warranty.warranty_start_date))
                period = vals.get('warranty_period', warranty.warranty_period)
                
                # Calculate end date
                year = start_date.year + (start_date.month + period - 1) // 12
                month = (start_date.month + period - 1) % 12 + 1
                day = min(start_date.day, [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
                vals['warranty_end_date'] = fields.Date.to_string(fields.Date(year, month, day))
        
        result = super(ProductWarranty, self).write(vals)
        
        # Update state if start date changed
        if 'warranty_start_date' in vals:
            for warranty in self:
                if warranty.warranty_start_date <= fields.Date.today() and warranty.state == 'draft':
                    warranty.state = 'active'
        
        return result

    @api.constrains('warranty_start_date', 'warranty_end_date')
    def _check_dates(self):
        for warranty in self:
            if warranty.warranty_start_date and warranty.warranty_end_date:
                if warranty.warranty_end_date < warranty.warranty_start_date:
                    raise ValidationError(_('Warranty end date cannot be before start date.'))

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            product_tmpl = self.product_id.product_tmpl_id
            if product_tmpl.has_warranty:
                self.warranty_type = product_tmpl.warranty_type
                self.warranty_period = product_tmpl.warranty_period
                self.warranty_price = product_tmpl.warranty_price

    @api.onchange('warranty_start_date', 'warranty_period')
    def _onchange_warranty_period(self):
        if self.warranty_start_date and self.warranty_period:
            start_date = self.warranty_start_date
            months = self.warranty_period
            year = start_date.year + (start_date.month + months - 1) // 12
            month = (start_date.month + months - 1) % 12 + 1
            day = min(start_date.day, [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
            self.warranty_end_date = fields.Date(year, month, day)

    def action_activate(self):
        """Activate warranty"""
        self.write({'state': 'active'})
        return True

    def action_cancel(self):
        """Cancel warranty"""
        self.write({'state': 'cancelled'})
        return True

    def action_view_claims(self):
        """Open warranty claims"""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('product_warranty_claim.action_product_warranty_claim')
        action['domain'] = [('warranty_id', '=', self.id)]
        action['context'] = {'default_warranty_id': self.id}
        return action

    def action_view_renewals(self):
        """Open warranty renewals"""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('product_warranty_claim.action_product_warranty_renewal')
        action['domain'] = [('warranty_id', '=', self.id)]
        action['context'] = {'default_warranty_id': self.id}
        return action

    def action_view_invoice(self):
        """Open invoice"""
        self.ensure_one()
        if not self.invoice_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_create_invoice(self):
        """Create invoice for paid warranty"""
        self.ensure_one()
        if self.warranty_type != 'paid':
            raise UserError(_('Invoice can only be created for paid warranties.'))
        
        if self.invoice_id:
            raise UserError(_('Invoice already exists for this warranty.'))
        
        # Create invoice
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'name': f'Warranty - {self.name}',
                'quantity': 1,
                'price_unit': self.warranty_price,
            })],
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_id = invoice.id
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }
