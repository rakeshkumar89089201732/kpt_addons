# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ProductWarrantyRenewal(models.Model):
    _name = 'product.warranty.renewal'
    _description = 'Warranty Renewal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'renewal_date desc, name desc'

    name = fields.Char(
        string='Renewal Number',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _('New'),
        tracking=True
    )
    
    warranty_id = fields.Many2one(
        'product.warranty',
        string='Original Warranty',
        required=True,
        ondelete='cascade',
        tracking=True,
        help='Original warranty being renewed'
    )
    
    new_warranty_id = fields.Many2one(
        'product.warranty',
        string='New Warranty',
        readonly=True,
        help='New warranty created from renewal'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        related='warranty_id.partner_id',
        string='Customer',
        store=True,
        readonly=True
    )
    
    product_id = fields.Many2one(
        'product.product',
        related='warranty_id.product_id',
        string='Product',
        store=True,
        readonly=True
    )
    
    serial_number = fields.Char(
        related='warranty_id.serial_number',
        string='Serial Number',
        store=True,
        readonly=True
    )
    
    renewal_date = fields.Date(
        string='Renewal Date',
        required=True,
        default=fields.Date.today,
        tracking=True,
        help='Date when warranty is renewed'
    )
    
    renewal_period = fields.Integer(
        string='Renewal Period (Months)',
        required=True,
        default=12,
        tracking=True,
        help='Warranty period for renewal in months'
    )
    
    renewal_start_date = fields.Date(
        string='Renewal Start Date',
        required=True,
        tracking=True,
        help='Start date for renewed warranty'
    )
    
    renewal_end_date = fields.Date(
        string='Renewal End Date',
        required=True,
        tracking=True,
        help='End date for renewed warranty'
    )
    
    renewal_price = fields.Float(
        string='Renewal Price',
        default=0.0,
        tracking=True,
        help='Price paid for warranty renewal'
    )
    
    warranty_type = fields.Selection([
        ('free', 'Free Warranty'),
        ('paid', 'Paid Warranty'),
    ], string='Warranty Type', required=True, default='free', tracking=True)
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        readonly=True,
        help='Invoice generated for paid renewal'
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    note = fields.Text(string='Notes')
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='warranty_id.company_id',
        store=True,
        readonly=True
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('product.warranty.renewal') or _('New')
        
        # Calculate renewal end date if not provided
        if 'renewal_start_date' in vals and 'renewal_period' in vals:
            if 'renewal_end_date' not in vals or not vals.get('renewal_end_date'):
                start_date = fields.Date.from_string(vals['renewal_start_date'])
                months = vals['renewal_period']
                year = start_date.year + (start_date.month + months - 1) // 12
                month = (start_date.month + months - 1) % 12 + 1
                day = min(start_date.day, [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
                vals['renewal_end_date'] = fields.Date.to_string(fields.Date(year, month, day))
        
        return super(ProductWarrantyRenewal, self).create(vals)

    @api.constrains('renewal_start_date', 'renewal_end_date')
    def _check_dates(self):
        for renewal in self:
            if renewal.renewal_start_date and renewal.renewal_end_date:
                if renewal.renewal_end_date < renewal.renewal_start_date:
                    raise ValidationError(_('Renewal end date cannot be before start date.'))

    @api.onchange('warranty_id')
    def _onchange_warranty_id(self):
        if self.warranty_id:
            self.warranty_type = self.warranty_id.warranty_type
            self.renewal_period = self.warranty_id.warranty_period
            # Set renewal start date to original warranty end date or today, whichever is later
            if self.warranty_id.warranty_end_date:
                self.renewal_start_date = max(self.warranty_id.warranty_end_date, fields.Date.today())
            else:
                self.renewal_start_date = fields.Date.today()

    @api.onchange('renewal_start_date', 'renewal_period')
    def _onchange_renewal_period(self):
        if self.renewal_start_date and self.renewal_period:
            start_date = self.renewal_start_date
            months = self.renewal_period
            year = start_date.year + (start_date.month + months - 1) // 12
            month = (start_date.month + months - 1) % 12 + 1
            day = min(start_date.day, [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
            self.renewal_end_date = fields.Date(year, month, day)

    def action_confirm(self):
        """Confirm renewal"""
        self.write({'state': 'confirmed'})
        return True

    def action_complete(self):
        """Complete renewal and create new warranty"""
        self.ensure_one()
        if self.state != 'confirmed':
            raise UserError(_('Renewal must be confirmed before completion.'))
        
        # Create new warranty
        warranty_vals = {
            'partner_id': self.partner_id.id,
            'product_id': self.product_id.id,
            'serial_number': self.serial_number,
            'warranty_type': self.warranty_type,
            'warranty_start_date': self.renewal_start_date,
            'warranty_end_date': self.renewal_end_date,
            'warranty_period': self.renewal_period,
            'warranty_price': self.renewal_price,
            'state': 'active',
        }
        
        new_warranty = self.env['product.warranty'].create(warranty_vals)
        self.new_warranty_id = new_warranty.id
        self.state = 'completed'
        
        # Create invoice if paid renewal
        if self.warranty_type == 'paid' and self.renewal_price > 0:
            self.action_create_invoice()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('New Warranty'),
            'res_model': 'product.warranty',
            'res_id': new_warranty.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_create_invoice(self):
        """Create invoice for paid renewal"""
        self.ensure_one()
        if self.warranty_type != 'paid':
            raise UserError(_('Invoice can only be created for paid renewals.'))
        
        if self.invoice_id:
            raise UserError(_('Invoice already exists for this renewal.'))
        
        # Create invoice
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'name': f'Warranty Renewal - {self.name}',
                'quantity': 1,
                'price_unit': self.renewal_price,
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

    def action_cancel(self):
        """Cancel renewal"""
        self.write({'state': 'cancelled'})
        return True

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
