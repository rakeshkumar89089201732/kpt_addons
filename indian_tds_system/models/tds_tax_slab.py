# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta

class TdsTaxSlab(models.Model):
    _name = 'tds.tax.slab'
    _description = 'TDS Tax Slab Configuration'
    _order = 'financial_year desc, regime_type'

    name = fields.Char(string='Slab Name', required=True)
    active = fields.Boolean(default=True)
    financial_year = fields.Char(string='Financial Year', required=True, help="Example: 2024-25")
    date_start = fields.Date(string='FY Start Date', required=True)
    date_end = fields.Date(string='FY End Date', required=True)
    
    regime_type = fields.Selection([
        ('old', 'Old Tax Regime'),
        ('new', 'New Tax Regime (Section 115BAC)')
    ], string='Tax Regime', required=True, default='new')
    
    age_category = fields.Selection([
        ('below_60', 'Below 60 years'),
        ('senior_60_80', 'Senior Citizen (60-80 years)'),
        ('super_senior_80', 'Super Senior Citizen (80+ years)')
    ], string='Age Category', required=True, default='below_60')
    
    slab_line_ids = fields.One2many('tds.tax.slab.line', 'slab_id', string='Tax Slab Lines')
    
    # Rebate Configuration
    enable_rebate_87a = fields.Boolean(string='Enable Rebate u/s 87A', default=False)
    rebate_87a_income_limit = fields.Float(string='87A Income Limit', default=500000)
    rebate_87a_max_amount = fields.Float(string='87A Max Rebate Amount', default=12500)
    
    # Standard Deduction
    standard_deduction_amount = fields.Float(string='Standard Deduction', default=50000)
    
    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_start >= record.date_end:
                raise ValidationError('Start date must be before end date.')
    
    @api.onchange('date_start')
    def _onchange_date_start(self):
        if self.date_start:
            year = self.date_start.year
            self.date_end = self.date_start.replace(year=year + 1) - timedelta(days=1)
            self.financial_year = f"{year}-{str(year + 1)[2:]}"
    
    def get_tax_calculation(self, annual_income, deductions=0.0):
        """Calculate tax based on slab configuration"""
        self.ensure_one()
        
        # Apply standard deduction
        taxable_income = annual_income - self.standard_deduction_amount - deductions
        
        if taxable_income <= 0:
            return {
                'taxable_income': 0.0,
                'tax_before_rebate': 0.0,
                'rebate_87a': 0.0,
                'tax_after_rebate': 0.0,
                'surcharge': 0.0,
                'cess': 0.0,
                'total_tax': 0.0
            }
        
        # Calculate tax from slabs
        tax_amount = 0.0
        for line in self.slab_line_ids.sorted('income_from'):
            if taxable_income > line.income_from:
                taxable_in_slab = min(taxable_income, line.income_to or float('inf')) - line.income_from
                if taxable_in_slab > 0:
                    tax_amount += taxable_in_slab * (line.tax_rate / 100.0)
        
        # Apply rebate u/s 87A
        rebate_87a = 0.0
        if self.enable_rebate_87a and taxable_income <= self.rebate_87a_income_limit:
            rebate_87a = min(tax_amount, self.rebate_87a_max_amount)
        
        tax_after_rebate = max(tax_amount - rebate_87a, 0.0)
        
        # Calculate surcharge
        surcharge_rate = self._get_surcharge_rate(taxable_income)
        surcharge = tax_after_rebate * (surcharge_rate / 100.0)
        
        # Calculate cess (4% on tax + surcharge)
        cess = (tax_after_rebate + surcharge) * 0.04
        
        total_tax = tax_after_rebate + surcharge + cess
        
        return {
            'taxable_income': taxable_income,
            'tax_before_rebate': tax_amount,
            'rebate_87a': rebate_87a,
            'tax_after_rebate': tax_after_rebate,
            'surcharge': surcharge,
            'surcharge_rate': surcharge_rate,
            'cess': cess,
            'total_tax': total_tax
        }
    
    def _get_surcharge_rate(self, taxable_income):
        """Get applicable surcharge rate based on income"""
        if taxable_income <= 5000000:  # Up to 50 Lakh
            return 0.0
        elif taxable_income <= 10000000:  # 50L to 1 Cr
            return 10.0
        elif taxable_income <= 20000000:  # 1 Cr to 2 Cr
            return 15.0
        elif taxable_income <= 50000000:  # 2 Cr to 5 Cr
            return 25.0
        else:  # Above 5 Cr
            return 37.0


class TdsTaxSlabLine(models.Model):
    _name = 'tds.tax.slab.line'
    _description = 'TDS Tax Slab Line'
    _order = 'income_from'

    slab_id = fields.Many2one('tds.tax.slab', string='Tax Slab', required=True, ondelete='cascade')
    income_from = fields.Float(string='Income From', required=True)
    income_to = fields.Float(string='Income To')
    tax_rate = fields.Float(string='Tax Rate (%)', required=True)
    description = fields.Char(string='Description')
    
    @api.constrains('income_from', 'income_to', 'tax_rate')
    def _check_slab_line(self):
        for record in self:
            if record.income_to and record.income_from >= record.income_to:
                raise ValidationError('Income From must be less than Income To.')
            if record.tax_rate < 0 or record.tax_rate > 100:
                raise ValidationError('Tax rate must be between 0 and 100.')
