# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime

class TdsCertificate(models.Model):
    _name = 'tds.certificate'
    _description = 'TDS Certificate (Form 16)'
    _order = 'certificate_number desc, financial_year desc'
    _rec_name = 'certificate_number'

    # Basic Information
    certificate_number = fields.Char(string='Certificate Number', required=True, copy=False)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    employer_id = fields.Many2one('res.company', string='Employer', required=True, default=lambda self: self.env.company)
    financial_year = fields.Char(string='Financial Year', required=True)
    assessment_year = fields.Char(string='Assessment Year', required=True)
    
    # Period Information
    period_from = fields.Date(string='Period From', required=True)
    period_to = fields.Date(string='Period To', required=True)
    
    # Employee Details
    employee_pan = fields.Char(string='Employee PAN', related='employee_id.pan_number', store=True)
    employee_address = fields.Text(string='Employee Address')
    
    # Employer Details
    employer_pan = fields.Char(string='Employer PAN', related='employer_id.vat', store=True)
    employer_tan = fields.Char(string='Employer TAN', related='employer_id.tan_number', store=True)
    employer_address = fields.Char(string='Employer Address', related='employer_id.partner_id.contact_address', store=True)
    
    # Income and Tax Details
    gross_salary = fields.Float(string='Gross Salary')
    allowances = fields.Float(string='Allowances')
    perquisites = fields.Float(string='Perquisites')
    profits_in_lieu = fields.Float(string='Profits in lieu of Salary')
    total_income = fields.Float(string='Total Income', compute='_compute_totals', store=True)
    
    # Deductions
    standard_deduction = fields.Float(string='Standard Deduction')
    entertainment_allowance = fields.Float(string='Entertainment Allowance')
    professional_tax = fields.Float(string='Professional Tax')
    other_deductions = fields.Float(string='Other Deductions')
    total_deductions = fields.Float(string='Total Deductions', compute='_compute_totals', store=True)
    
    # Taxable Income
    income_chargeable = fields.Float(string='Income Chargeable to Tax', compute='_compute_totals', store=True)
    
    # Tax Calculations
    tax_on_income = fields.Float(string='Tax on Income')
    surcharge = fields.Float(string='Surcharge')
    cess = fields.Float(string='Education Cess')
    total_tax = fields.Float(string='Total Tax', compute='_compute_totals', store=True)
    
    # TDS Details
    tds_deducted = fields.Float(string='TDS Deducted', required=True)
    
    # Certificate Details
    certificate_date = fields.Date(string='Certificate Date', default=fields.Date.today)
    issued_by = fields.Many2one('res.users', string='Issued By', default=lambda self: self.env.user)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft')
    
    # Related Records
    calculation_id = fields.Many2one('tds.calculation', string='TDS Calculation')
    challan_ids = fields.Many2many('tds.challan', string='Related Challans')
    
    # Attachments
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    
    @api.depends('gross_salary', 'allowances', 'perquisites', 'profits_in_lieu')
    def _compute_totals(self):
        for record in self:
            record.total_income = (record.gross_salary + record.allowances + 
                                 record.perquisites + record.profits_in_lieu)
            
            record.total_deductions = (record.standard_deduction + record.entertainment_allowance + 
                                     record.professional_tax + record.other_deductions)
            
            record.income_chargeable = record.total_income - record.total_deductions
            
            record.total_tax = record.tax_on_income + record.surcharge + record.cess
    
    @api.model
    def create(self, vals):
        if not vals.get('certificate_number'):
            vals['certificate_number'] = self.env['ir.sequence'].next_by_code('tds.certificate') or '/'
        return super().create(vals)
    
    @api.constrains('period_from', 'period_to')
    def _check_period_dates(self):
        for record in self:
            if record.period_from >= record.period_to:
                raise ValidationError('Period From must be before Period To.')
    
    def action_issue_certificate(self):
        """Issue the TDS certificate"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError('Only draft certificates can be issued.')
        
        # Validate required fields
        if not self.employee_pan:
            raise UserError('Employee PAN is required to issue certificate.')
        if not self.employer_tan:
            raise UserError('Employer TAN is required to issue certificate.')
        
        self.state = 'issued'
        self.certificate_date = fields.Date.today()
        return True
    
    def action_cancel_certificate(self):
        """Cancel the TDS certificate"""
        self.ensure_one()
        if self.state == 'cancelled':
            raise UserError('Certificate is already cancelled.')
        
        self.state = 'cancelled'
        return True
    
    def action_reset_to_draft(self):
        """Reset certificate to draft"""
        self.ensure_one()
        self.state = 'draft'
        return True
    
    def action_print_certificate(self):
        """Print TDS certificate"""
        self.ensure_one()
        return self.env.ref('indian_tds_system.action_report_tds_certificate').report_action(self)
    
    def generate_from_calculation(self, calculation_id):
        """Generate certificate from TDS calculation"""
        calculation = self.env['tds.calculation'].browse(calculation_id)
        if not calculation.exists():
            raise UserError('Invalid TDS calculation.')
        
        vals = {
            'employee_id': calculation.employee_id.id,
            'financial_year': calculation.financial_year,
            'period_from': calculation.date_from,
            'period_to': calculation.date_to,
            'gross_salary': calculation.annual_salary,
            'total_income': calculation.gross_total_income,
            'total_deductions': calculation.total_deductions,
            'income_chargeable': calculation.taxable_income,
            'tax_on_income': calculation.tax_after_rebate,
            'surcharge': calculation.surcharge,
            'cess': calculation.cess,
            'tds_deducted': calculation.total_tax_liability,
            'calculation_id': calculation.id,
        }
        
        return self.create(vals)
