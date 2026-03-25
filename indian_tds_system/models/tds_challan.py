# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime

class TdsChallan(models.Model):
    _name = 'tds.challan'
    _description = 'TDS Challan Management'
    _order = 'challan_date desc, challan_number desc'
    _rec_name = 'challan_number'

    # Basic Information
    challan_number = fields.Char(string='Challan Number', required=True, copy=False)
    challan_date = fields.Date(string='Challan Date', required=True, default=fields.Date.today)
    bank_name = fields.Char(string='Bank Name', required=True)
    bank_branch = fields.Char(string='Bank Branch')
    
    # Period Information
    financial_year = fields.Char(string='Financial Year', required=True)
    quarter = fields.Selection([
        ('q1', 'Q1 (Apr-Jun)'),
        ('q2', 'Q2 (Jul-Sep)'),
        ('q3', 'Q3 (Oct-Dec)'),
        ('q4', 'Q4 (Jan-Mar)')
    ], string='Quarter', required=True)
    
    assessment_year = fields.Char(string='Assessment Year', required=True)
    
    # Company Information
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    company_pan = fields.Char(string='Company PAN', related='company_id.vat', store=True)
    company_tan = fields.Char(string='Company TAN', related='company_id.tan_number', store=True)
    
    # Challan Details
    challan_line_ids = fields.One2many('tds.challan.line', 'challan_id', string='Challan Lines')
    
    # Amounts
    total_tax_deposited = fields.Float(string='Total Tax Deposited', compute='_compute_totals', store=True)
    interest_amount = fields.Float(string='Interest Amount')
    penalty_amount = fields.Float(string='Penalty Amount')
    total_amount = fields.Float(string='Total Amount', compute='_compute_totals', store=True)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('deposited', 'Deposited'),
        ('reconciled', 'Reconciled'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft')
    
    # Additional Information
    remarks = fields.Text(string='Remarks')
    attachment_ids = fields.Many2many('ir.attachment', string='Supporting Documents')
    
    @api.depends('challan_line_ids.amount', 'interest_amount', 'penalty_amount')
    def _compute_totals(self):
        for record in self:
            record.total_tax_deposited = sum(record.challan_line_ids.mapped('amount'))
            record.total_amount = record.total_tax_deposited + record.interest_amount + record.penalty_amount
    
    @api.model
    def create(self, vals):
        if not vals.get('challan_number'):
            vals['challan_number'] = self.env['ir.sequence'].next_by_code('tds.challan') or '/'
        return super().create(vals)
    
    def action_deposit(self):
        """Mark challan as deposited"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError('Only draft challans can be deposited.')
        
        if not self.challan_line_ids:
            raise UserError('Please add at least one challan line.')
        
        self.state = 'deposited'
        return True
    
    def action_reconcile(self):
        """Mark challan as reconciled"""
        self.ensure_one()
        if self.state != 'deposited':
            raise UserError('Only deposited challans can be reconciled.')
        
        self.state = 'reconciled'
        return True
    
    def action_cancel(self):
        """Cancel challan"""
        self.ensure_one()
        if self.state == 'reconciled':
            raise UserError('Reconciled challans cannot be cancelled.')
        
        self.state = 'cancelled'
        return True
    
    def action_reset_to_draft(self):
        """Reset to draft"""
        self.ensure_one()
        self.state = 'draft'
        return True


class TdsChallanLine(models.Model):
    _name = 'tds.challan.line'
    _description = 'TDS Challan Line'
    _order = 'section_code'

    challan_id = fields.Many2one('tds.challan', string='Challan', required=True, ondelete='cascade')
    
    # Section Information
    section_code = fields.Selection([
        ('194A', '194A - Interest on Securities'),
        ('194B', '194B - Winnings from Lottery'),
        ('194C', '194C - Payments to Contractors'),
        ('194D', '194D - Insurance Commission'),
        ('194H', '194H - Commission or Brokerage'),
        ('194I', '194I - Rent'),
        ('194J', '194J - Professional/Technical Services'),
        ('194K', '194K - Income from Units'),
        ('194LA', '194LA - Compensation for Land'),
        ('194M', '194M - Contractual Payments'),
        ('194N', '194N - Cash Withdrawals'),
        ('194O', '194O - E-commerce Transactions'),
        ('194P', '194P - Winnings from Online Games'),
        ('194Q', '194Q - Purchase of Goods'),
        ('194S', '194S - Cryptocurrency Payments'),
        ('salary', 'Salary')
    ], string='Section Code', required=True)
    
    # Amount Details
    amount = fields.Float(string='Amount', required=True)
    description = fields.Char(string='Description')
    
    # Employee Details (for salary TDS)
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    employee_count = fields.Integer(string='Number of Employees', compute='_compute_employee_count', store=True)
    
    @api.depends('employee_ids')
    def _compute_employee_count(self):
        for record in self:
            record.employee_count = len(record.employee_ids)
    
    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError('Amount must be greater than zero.')
