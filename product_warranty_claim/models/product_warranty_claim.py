# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ProductWarrantyClaim(models.Model):
    _name = 'product.warranty.claim'
    _description = 'Warranty Claim'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'claim_date desc, name desc'

    name = fields.Char(
        string='Claim Number',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _('New'),
        tracking=True
    )
    
    warranty_id = fields.Many2one(
        'product.warranty',
        string='Warranty',
        required=True,
        ondelete='cascade',
        tracking=True,
        help='Warranty for this claim'
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
    
    claim_date = fields.Date(
        string='Claim Date',
        required=True,
        default=fields.Date.today,
        tracking=True,
        help='Date when the claim was made'
    )
    
    issue_description = fields.Text(
        string='Issue Description',
        required=True,
        tracking=True,
        help='Description of the issue or problem'
    )
    
    resolution = fields.Text(
        string='Resolution',
        tracking=True,
        help='Resolution or action taken for this claim'
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    is_within_warranty = fields.Boolean(
        string='Within Warranty Period',
        compute='_compute_is_within_warranty',
        store=True,
        help='Whether the claim is within warranty period'
    )
    
    claim_type = fields.Selection([
        ('repair', 'Repair'),
        ('replacement', 'Replacement'),
        ('refund', 'Refund'),
        ('other', 'Other'),
    ], string='Claim Type', default='repair', tracking=True)
    
    cost = fields.Float(
        string='Claim Cost',
        default=0.0,
        tracking=True,
        help='Cost associated with this claim'
    )
    
    assigned_to = fields.Many2one(
        'res.users',
        string='Assigned To',
        tracking=True,
        help='User assigned to handle this claim'
    )
    
    resolution_date = fields.Date(
        string='Resolution Date',
        tracking=True,
        help='Date when the claim was resolved'
    )
    
    note = fields.Text(string='Notes')
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='warranty_id.company_id',
        store=True,
        readonly=True
    )

    @api.depends('claim_date', 'warranty_id.warranty_end_date')
    def _compute_is_within_warranty(self):
        for claim in self:
            if claim.warranty_id and claim.warranty_id.warranty_end_date:
                claim.is_within_warranty = (
                    claim.claim_date <= claim.warranty_id.warranty_end_date and
                    claim.warranty_id.state == 'active'
                )
            else:
                claim.is_within_warranty = False

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('product.warranty.claim') or _('New')
        return super(ProductWarrantyClaim, self).create(vals)

    @api.constrains('claim_date', 'warranty_id')
    def _check_claim_date(self):
        for claim in self:
            if claim.warranty_id and claim.warranty_id.warranty_start_date:
                if claim.claim_date < claim.warranty_id.warranty_start_date:
                    raise ValidationError(_('Claim date cannot be before warranty start date.'))

    def action_submit(self):
        """Submit claim"""
        self.write({'state': 'submitted'})
        return True

    def action_start_progress(self):
        """Start processing claim"""
        self.write({'state': 'in_progress'})
        return True

    def action_resolve(self):
        """Resolve claim"""
        self.write({
            'state': 'resolved',
            'resolution_date': fields.Date.today()
        })
        return True

    def action_reject(self):
        """Reject claim"""
        self.write({'state': 'rejected'})
        return True

    def action_cancel(self):
        """Cancel claim"""
        self.write({'state': 'cancelled'})
        return True

    @api.onchange('warranty_id')
    def _onchange_warranty_id(self):
        if self.warranty_id:
            if self.warranty_id.state == 'expired':
                return {
                    'warning': {
                        'title': _('Warning'),
                        'message': _('This warranty has expired. Claims may not be eligible.'),
                    }
                }
