# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime

class TdsCalculationWizard(models.TransientModel):
    _name = 'tds.calculation.wizard'
    _description = 'TDS Calculation Wizard'

    # Employee Selection
    employee_ids = fields.Many2many('hr.employee', string='Employees', required=True)
    all_employees = fields.Boolean(string='All Employees', default=False)
    
    # Period Selection
    financial_year = fields.Char(string='Financial Year', required=True)
    date_from = fields.Date(string='Period From', required=True)
    date_to = fields.Date(string='Period To', required=True)
    
    # Tax Configuration
    tax_regime = fields.Selection([
        ('old', 'Old Tax Regime'),
        ('new', 'New Tax Regime (Section 115BAC)')
    ], string='Default Tax Regime', default='new')
    
    # Options
    recalculate_existing = fields.Boolean(string='Recalculate Existing', default=False)
    auto_approve = fields.Boolean(string='Auto Approve', default=False)
    
    @api.onchange('all_employees')
    def _onchange_all_employees(self):
        if self.all_employees:
            self.employee_ids = self.env['hr.employee'].search([('active', '=', True)])
        else:
            self.employee_ids = False
    
    @api.onchange('date_from')
    def _onchange_date_from(self):
        if self.date_from:
            year = self.date_from.year
            if self.date_from.month >= 4:
                self.date_to = self.date_from.replace(year=year + 1, month=3, day=31)
                self.financial_year = f"{year}-{str(year + 1)[2:]}"
            else:
                self.date_to = self.date_from.replace(month=3, day=31)
                self.financial_year = f"{year - 1}-{str(year)[2:]}"
    
    def action_calculate_tds(self):
        """Calculate TDS for selected employees"""
        if not self.employee_ids:
            raise UserError('Please select at least one employee.')
        
        created_calculations = self.env['tds.calculation']
        
        for employee in self.employee_ids:
            # Check if calculation already exists
            existing = self.env['tds.calculation'].search([
                ('employee_id', '=', employee.id),
                ('financial_year', '=', self.financial_year),
                ('date_from', '=', self.date_from),
                ('date_to', '=', self.date_to)
            ])
            
            if existing and not self.recalculate_existing:
                continue
            
            if existing and self.recalculate_existing:
                existing.unlink()
            
            # Get employee's active contract
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'open')
            ], limit=1)
            
            # Create TDS calculation
            vals = {
                'employee_id': employee.id,
                'contract_id': contract.id if contract else False,
                'financial_year': self.financial_year,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'tax_regime': employee.preferred_tax_regime or self.tax_regime,
            }
            
            calculation = self.env['tds.calculation'].create(vals)
            calculation.action_calculate()
            
            if self.auto_approve:
                calculation.action_approve()
            
            created_calculations |= calculation
        
        # Return action to view created calculations
        return {
            'type': 'ir.actions.act_window',
            'name': 'TDS Calculations',
            'res_model': 'tds.calculation',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', created_calculations.ids)],
            'target': 'current',
        }
