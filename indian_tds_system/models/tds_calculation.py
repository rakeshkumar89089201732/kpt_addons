# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import calendar

class TdsCalculation(models.Model):
    _name = 'tds.calculation'
    _description = 'TDS Calculation'
    _order = 'financial_year desc, employee_id'
    _rec_name = 'display_name'

    # Basic Information
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    contract_id = fields.Many2one('hr.contract', string='Contract')
    financial_year = fields.Char(string='Financial Year', required=True)
    date_from = fields.Date(string='Period From', required=True)
    date_to = fields.Date(string='Period To', required=True)
    
    # Tax Regime Selection
    tax_regime = fields.Selection([
        ('old', 'Old Tax Regime'),
        ('new', 'New Tax Regime (Section 115BAC)')
    ], string='Tax Regime', required=True, default='new')
    
    tax_slab_id = fields.Many2one('tds.tax.slab', string='Tax Slab')
    
    # Income Details
    annual_salary = fields.Float(string='Annual Salary', compute='_compute_annual_salary', store=True)
    other_income = fields.Float(string='Other Income')
    previous_employer_salary = fields.Float(string='Previous Employer Salary')
    previous_employer_tds = fields.Float(string='Previous Employer TDS')
    
    # Deductions
    deduction_line_ids = fields.One2many('tds.deduction.line', 'calculation_id', string='Deduction Lines')
    total_deductions = fields.Float(string='Total Deductions', compute='_compute_total_deductions', store=True)
    
    # Tax Calculations
    gross_total_income = fields.Float(string='Gross Total Income', compute='_compute_tax_calculations', store=True)
    taxable_income = fields.Float(string='Taxable Income', compute='_compute_tax_calculations', store=True)
    tax_before_rebate = fields.Float(string='Tax Before Rebate', compute='_compute_tax_calculations', store=True)
    rebate_87a = fields.Float(string='Rebate u/s 87A', compute='_compute_tax_calculations', store=True)
    tax_after_rebate = fields.Float(string='Tax After Rebate', compute='_compute_tax_calculations', store=True)
    surcharge = fields.Float(string='Surcharge', compute='_compute_tax_calculations', store=True)
    surcharge_rate = fields.Float(string='Surcharge Rate (%)', compute='_compute_tax_calculations', store=True)
    cess = fields.Float(string='Education Cess', compute='_compute_tax_calculations', store=True)
    total_tax_liability = fields.Float(string='Total Tax Liability', compute='_compute_tax_calculations', store=True)
    
    # TDS Calculations
    tds_already_deducted = fields.Float(string='TDS Already Deducted', compute='_compute_tds_calculations', store=True)
    remaining_tds = fields.Float(string='Remaining TDS', compute='_compute_tds_calculations', store=True)
    monthly_tds = fields.Float(string='Monthly TDS', compute='_compute_tds_calculations', store=True)
    
    # Monthly Breakdown
    monthly_breakdown_ids = fields.One2many('tds.monthly.breakdown', 'calculation_id', string='Monthly Breakdown')
    
    # Status and Control
    state = fields.Selection([
        ('draft', 'Draft'),
        ('calculated', 'Calculated'),
        ('approved', 'Approved'),
        ('locked', 'Locked')
    ], string='Status', default='draft')
    
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    
    @api.depends('employee_id', 'financial_year')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.employee_id.name or 'Unknown'} - {record.financial_year or 'Unknown'}"
    
    @api.depends('contract_id', 'date_from', 'date_to', 'employee_id')
    def _compute_annual_salary(self):
        for record in self:
            if record.employee_id and record.contract_id and record.date_from and record.date_to:
                # Find all career updates for this employee within the financial year
                updates = self.env['hr.career.update'].search([
                    ('employee_id', '=', record.employee_id.id),
                    ('state', '=', 'applied'),
                    ('is_increment', '=', True),
                    ('effective_date', '>=', record.date_from),
                    ('effective_date', '<=', record.date_to)
                ], order='effective_date asc')

                total_annual_salary = 0.0
                current_month_date = record.date_from.replace(day=1)
                end_month_date = record.date_to.replace(day=1)
                
                while current_month_date <= end_month_date:
                    # Find the wage active for this specific month
                    applicable_update = self.env['hr.career.update'].search([
                        ('employee_id', '=', record.employee_id.id),
                        ('state', '=', 'applied'),
                        ('is_increment', '=', True),
                        ('effective_date', '<=', current_month_date + relativedelta(day=31))
                    ], order='effective_date desc', limit=1)
                    
                    if applicable_update:
                        monthly_wage = applicable_update.new_wage
                    else:
                        monthly_wage = record.contract_id.wage
                    
                    total_annual_salary += monthly_wage
                    current_month_date += relativedelta(months=1)
                
                record.annual_salary = total_annual_salary
            else:
                record.annual_salary = 0.0
    
    @api.depends('deduction_line_ids.allowed_amount')
    def _compute_total_deductions(self):
        for record in self:
            record.total_deductions = sum(record.deduction_line_ids.mapped('allowed_amount'))
    
    @api.depends('annual_salary', 'other_income', 'previous_employer_salary', 'total_deductions', 'tax_slab_id')
    def _compute_tax_calculations(self):
        for record in self:
            if not record.tax_slab_id:
                record.update({
                    'gross_total_income': 0.0,
                    'taxable_income': 0.0,
                    'tax_before_rebate': 0.0,
                    'rebate_87a': 0.0,
                    'tax_after_rebate': 0.0,
                    'surcharge': 0.0,
                    'surcharge_rate': 0.0,
                    'cess': 0.0,
                    'total_tax_liability': 0.0,
                })
                continue
            
            # Calculate gross total income
            gross_income = record.annual_salary + record.other_income + record.previous_employer_salary
            
            # Get tax calculation from slab
            tax_calc = record.tax_slab_id.get_tax_calculation(gross_income, record.total_deductions)
            
            record.update({
                'gross_total_income': gross_income,
                'taxable_income': tax_calc['taxable_income'],
                'tax_before_rebate': tax_calc['tax_before_rebate'],
                'rebate_87a': tax_calc['rebate_87a'],
                'tax_after_rebate': tax_calc['tax_after_rebate'],
                'surcharge': tax_calc['surcharge'],
                'surcharge_rate': tax_calc.get('surcharge_rate', 0.0),
                'cess': tax_calc['cess'],
                'total_tax_liability': tax_calc['total_tax'],
            })
    
    @api.depends('total_tax_liability', 'previous_employer_tds', 'date_from', 'date_to')
    def _compute_tds_calculations(self):
        for record in self:
            # Calculate remaining months for TDS deduction
            if record.date_from and record.date_to:
                today = fields.Date.today()
                remaining_months = 0
                
                current_date = max(today.replace(day=1), record.date_from.replace(day=1))
                end_date = record.date_to.replace(day=1)
                
                while current_date <= end_date:
                    remaining_months += 1
                    current_date += relativedelta(months=1)
                
                record.tds_already_deducted = record.previous_employer_tds
                record.remaining_tds = max(record.total_tax_liability - record.previous_employer_tds, 0.0)
                record.monthly_tds = record.remaining_tds / remaining_months if remaining_months > 0 else 0.0
            else:
                record.tds_already_deducted = 0.0
                record.remaining_tds = 0.0
                record.monthly_tds = 0.0
    
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            # Auto-fill contract
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', self.employee_id.id),
                ('state', '=', 'open')
            ], limit=1)
            if contract:
                self.contract_id = contract
    
    @api.onchange('tax_regime', 'date_from')
    def _onchange_tax_regime_date(self):
        if self.tax_regime and self.date_from:
            # Find appropriate tax slab
            slab = self.env['tds.tax.slab'].search([
                ('regime_type', '=', self.tax_regime),
                ('date_start', '<=', self.date_from),
                ('date_end', '>=', self.date_from),
                ('active', '=', True)
            ], limit=1)
            if slab:
                self.tax_slab_id = slab
    
    def action_calculate(self):
        """Calculate TDS and generate monthly breakdown"""
        self.ensure_one()
        self._generate_monthly_breakdown()
        self.state = 'calculated'
        return True
    
    def action_approve(self):
        """Approve TDS calculation"""
        self.ensure_one()
        if self.state != 'calculated':
            raise UserError('TDS calculation must be calculated before approval.')
        self.state = 'approved'
        return True
    
    def action_lock(self):
        """Lock TDS calculation"""
        self.ensure_one()
        if self.state != 'approved':
            raise UserError('TDS calculation must be approved before locking.')
        self.state = 'locked'
        return True
    
    def action_reset_to_draft(self):
        """Reset to draft state"""
        self.ensure_one()
        self.state = 'draft'
        return True
    
    def _generate_monthly_breakdown(self):
        """Generate monthly TDS breakdown"""
        self.ensure_one()
        
        # Clear existing breakdown
        self.monthly_breakdown_ids.unlink()
        
        if not self.date_from or not self.date_to:
            return
        
        breakdown_lines = []
        current_date = self.date_from.replace(day=1)
        end_date = self.date_to.replace(day=1)
        
        while current_date <= end_date:
            # Determine if this is a previous employer month
            is_previous_employer = current_date < fields.Date.today().replace(day=1)
            
            breakdown_lines.append({
                'calculation_id': self.id,
                'month_date': current_date,
                'month_name': current_date.strftime('%B %Y'),
                'is_previous_employer': is_previous_employer,
                'tds_amount': self.monthly_tds if not is_previous_employer else 0.0,
                'salary_amount': self.annual_salary / 12.0,  # Simplified calculation
            })
            
            current_date += relativedelta(months=1)
        
        self.env['tds.monthly.breakdown'].create(breakdown_lines)


class TdsMonthlyBreakdown(models.Model):
    _name = 'tds.monthly.breakdown'
    _description = 'TDS Monthly Breakdown'
    _order = 'month_date'

    calculation_id = fields.Many2one('tds.calculation', string='TDS Calculation', required=True, ondelete='cascade')
    month_date = fields.Date(string='Month', required=True)
    month_name = fields.Char(string='Month Name', required=True)
    is_previous_employer = fields.Boolean(string='Previous Employer Month', default=False)
    salary_amount = fields.Float(string='Salary Amount')
    tds_amount = fields.Float(string='TDS Amount')
    actual_tds_deducted = fields.Float(string='Actual TDS Deducted')
    remarks = fields.Text(string='Remarks')
