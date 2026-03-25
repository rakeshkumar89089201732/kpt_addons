# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # TDS Related Fields
    pan_number = fields.Char(string='PAN Number', size=10, help='Permanent Account Number', groups="hr.group_hr_user")
    aadhar_number = fields.Char(string='Aadhar Number', size=12, help='Aadhar Card Number', groups="hr.group_hr_user")
    tds_category_code = fields.Selection(
        [
            ("W", "Woman"),
            ("S", "Senior Citizen"),
            ("O", "Super Senior Citizen"),
            ("G", "Other"),
        ],
        string="TDS Category",
        groups="hr.group_hr_user",
    )
    
    # Tax Preferences
    preferred_tax_regime = fields.Selection([
        ('old', 'Old Tax Regime'),
        ('new', 'New Tax Regime (Section 115BAC)')
    ], string='Preferred Tax Regime', default='new', groups="hr.group_hr_user")
    
    # TDS Calculations
    tds_calculation_ids = fields.One2many('tds.calculation', 'employee_id', string='TDS Calculations')
    tds_certificate_ids = fields.One2many('tds.certificate', 'employee_id', string='TDS Certificates')
    
    # Current FY TDS Summary
    current_fy_tds_calculation_id = fields.Many2one(
        'tds.calculation', 
        string='Current FY TDS Calculation',
        compute='_compute_current_fy_tds',
        store=False
    )
    current_fy_annual_salary = fields.Float(
        string='Current FY Annual Salary',
        related='current_fy_tds_calculation_id.annual_salary'
    )
    current_fy_tax_liability = fields.Float(
        string='Current FY Tax Liability',
        related='current_fy_tds_calculation_id.total_tax_liability'
    )
    current_fy_monthly_tds = fields.Float(
        string='Current FY Monthly TDS',
        related='current_fy_tds_calculation_id.monthly_tds'
    )
    
    @api.depends('tds_calculation_ids')
    def _compute_current_fy_tds(self):
        for employee in self:
            current_date = fields.Date.today()
            # Find current financial year (April to March)
            if current_date.month >= 4:
                fy_start = current_date.replace(month=4, day=1)
                fy_end = current_date.replace(year=current_date.year + 1, month=3, day=31)
            else:
                fy_start = current_date.replace(year=current_date.year - 1, month=4, day=1)
                fy_end = current_date.replace(month=3, day=31)
            
            current_calculation = employee.tds_calculation_ids.filtered(
                lambda calc: calc.date_from <= current_date <= calc.date_to
            )
            
            employee.current_fy_tds_calculation_id = current_calculation[0] if current_calculation else False
    
    @api.constrains('pan_number')
    def _check_pan_number(self):
        for employee in self:
            if employee.pan_number:
                # Basic PAN validation (5 letters, 4 digits, 1 letter)
                import re
                if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', employee.pan_number):
                    raise ValidationError('Invalid PAN number format. Expected format: ABCDE1234F')
    
    @api.constrains('aadhar_number')
    def _check_aadhar_number(self):
        for employee in self:
            if employee.aadhar_number:
                if not employee.aadhar_number.isdigit() or len(employee.aadhar_number) != 12:
                    raise ValidationError('Aadhar number must be 12 digits.')
    
    def action_view_tds_calculations(self):
        """View employee's TDS calculations"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'TDS Calculations',
            'res_model': 'tds.calculation',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
    
    def action_view_tds_certificates(self):
        """View employee's TDS certificates"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'TDS Certificates',
            'res_model': 'tds.certificate',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
    
    def action_create_tds_calculation(self):
        """Create new TDS calculation for employee"""
        self.ensure_one()
        
        # Determine current financial year
        current_date = fields.Date.today()
        if current_date.month >= 4:
            fy_start = current_date.replace(month=4, day=1)
            fy_end = current_date.replace(year=current_date.year + 1, month=3, day=31)
            fy_name = f"{current_date.year}-{str(current_date.year + 1)[2:]}"
        else:
            fy_start = current_date.replace(year=current_date.year - 1, month=4, day=1)
            fy_end = current_date.replace(month=3, day=31)
            fy_name = f"{current_date.year - 1}-{str(current_date.year)[2:]}"
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create TDS Calculation',
            'res_model': 'tds.calculation',
            'view_mode': 'form',
            'context': {
                'default_employee_id': self.id,
                'default_financial_year': fy_name,
                'default_date_from': fy_start,
                'default_date_to': fy_end,
                'default_tax_regime': self.preferred_tax_regime or 'new',
            },
            'target': 'current',
        }
