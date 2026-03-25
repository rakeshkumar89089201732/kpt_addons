# -*- coding: utf-8 -*-

from odoo import models, fields, api

class HrContract(models.Model):
    _inherit = 'hr.contract'

    # TDS Configuration
    tds_applicable = fields.Boolean(string='TDS Applicable', default=True)
    tax_regime = fields.Selection([
        ('old', 'Old Tax Regime'),
        ('new', 'New Tax Regime (Section 115BAC)')
    ], string='Tax Regime', default='new')
    
    # Computed Fields
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')
    gross_salary = fields.Monetary(string='Gross Salary', compute='_compute_salary_components', store=True, currency_field='currency_id')
    ctc = fields.Monetary(string='Cost to Company', compute='_compute_salary_components', store=True, currency_field='currency_id')
    net_salary = fields.Monetary(string='Net Salary', compute='_compute_salary_components', store=True, currency_field='currency_id')
    
    # Components updated to Monetary
    basic_salary = fields.Monetary(string='Basic Salary', currency_field='currency_id')
    hra = fields.Monetary(string='House Rent Allowance', currency_field='currency_id')
    special_allowance = fields.Monetary(string='Special Allowance', currency_field='currency_id')
    transport_allowance = fields.Monetary(string='Transport Allowance', currency_field='currency_id')
    medical_allowance = fields.Monetary(string='Medical Allowance', currency_field='currency_id')
    other_allowances = fields.Monetary(string='Other Allowances', currency_field='currency_id')
    pf_employer = fields.Monetary(string='PF - Employer Contribution', currency_field='currency_id')
    esi_employer = fields.Monetary(string='ESI - Employer Contribution', currency_field='currency_id')
    gratuity = fields.Monetary(string='Gratuity', currency_field='currency_id')
    pf_employee = fields.Monetary(string='PF - Employee Contribution', currency_field='currency_id')
    esi_employee = fields.Monetary(string='ESI - Employee Contribution', currency_field='currency_id')
    professional_tax = fields.Monetary(string='Professional Tax', currency_field='currency_id')
    
    @api.depends('basic_salary', 'hra', 'special_allowance', 'transport_allowance', 
                 'medical_allowance', 'other_allowances', 'pf_employer', 'esi_employer', 
                 'gratuity', 'pf_employee', 'esi_employee', 'professional_tax')
    def _compute_salary_components(self):
        for contract in self:
            # Gross Salary (Taxable components)
            contract.gross_salary = (
                contract.basic_salary + contract.hra + contract.special_allowance +
                contract.transport_allowance + contract.medical_allowance + contract.other_allowances
            )
            
            # CTC (Including employer contributions)
            contract.ctc = (
                contract.gross_salary + contract.pf_employer + 
                contract.esi_employer + contract.gratuity
            )
            
            # Net Salary (After employee deductions)
            contract.net_salary = (
                contract.gross_salary - contract.pf_employee - 
                contract.esi_employee - contract.professional_tax
            )
    
    @api.onchange('wage', 'struct_id')
    def _onchange_salary_structure(self):
        """Pull components from salary structure rules if available"""
        for contract in self:
            if not contract.struct_id:
                # Fallback to standard distribution if no structure
                if contract.wage and not any([contract.basic_salary, contract.hra, contract.special_allowance]):
                    contract.basic_salary = contract.wage * 0.40
                    contract.hra = contract.wage * 0.20
                    contract.special_allowance = contract.wage * 0.40
                continue

            # Map salary rules to contract fields based on common Indian payroll codes
            # This logic assumes the structure has rules with these codes
            rules = contract.struct_id.rule_ids
            
            # Helper to get amount from rule code
            def get_rule_amount(code):
                rule = rules.filtered(lambda r: r.code == code)
                if not rule:
                    return 0.0
                # If it's a fixed amount, use it. Otherwise, estimate from wage.
                if rule.amount_select == 'fix':
                    return rule.amount_fix
                elif rule.amount_select == 'percentage':
                    return contract.wage * (rule.amount_percentage / 100.0)
                elif rule.amount_select == 'code' and 'wage' in rule.amount_python_compute:
                    # Very basic estimation for python code rules
                    try:
                        # This is a safe approximation for simple rules
                        return contract.wage * 0.12 if '0.12' in rule.amount_python_compute else 0.0
                    except:
                        return 0.0
                return 0.0

            contract.basic_salary = get_rule_amount('BASIC')
            contract.hra = get_rule_amount('HRA')
            contract.transport_allowance = get_rule_amount('TA')
            contract.medical_allowance = get_rule_amount('MA')
            
            # Deductions
            contract.pf_employee = get_rule_amount('PF')
            contract.esi_employee = get_rule_amount('ESI')
            contract.professional_tax = get_rule_amount('PT')
            
            # Employer contributions
            contract.pf_employer = get_rule_amount('EPF')
            contract.esi_employer = get_rule_amount('EESI')
            
            # Special Allowance often acts as a balancing figure in Indian CTC
            total_mapped = (contract.basic_salary + contract.hra + contract.transport_allowance + 
                           contract.medical_allowance + contract.pf_employer + contract.esi_employer)
            if contract.wage > total_mapped:
                contract.special_allowance = contract.wage - total_mapped
            else:
                contract.special_allowance = 0.0
    
    def get_annual_taxable_income(self):
        """Calculate annual taxable income for TDS"""
        self.ensure_one()
        monthly_taxable = self.gross_salary
        return monthly_taxable * 12
    
    def get_annual_deductions(self):
        """Calculate annual employee deductions"""
        self.ensure_one()
        monthly_deductions = self.pf_employee + self.esi_employee + self.professional_tax
        return monthly_deductions * 12
