# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class TdsSection(models.Model):
    _name = 'tds.section'
    _description = 'TDS Deduction Sections'
    _order = 'section_code'

    name = fields.Char(string='Section Name', required=True)
    section_code = fields.Char(string='Section Code', required=True, help="e.g., 80C, 80D, 80G")
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)
    
    applicable_regime = fields.Selection([
        ('old', 'Old Regime Only'),
        ('new', 'New Regime Only'),
        ('both', 'Both Regimes')
    ], string='Applicable Regime', required=True, default='old')
    
    max_deduction_limit = fields.Float(string='Maximum Deduction Limit')
    is_unlimited = fields.Boolean(string='Unlimited Deduction', default=False)
    
    subsection_ids = fields.One2many('tds.section.subsection', 'section_id', string='Sub-sections')
    
    @api.constrains('section_code')
    def _check_unique_section_code(self):
        for record in self:
            existing = self.search([
                ('section_code', '=', record.section_code),
                ('id', '!=', record.id)
            ])
            if existing:
                raise ValidationError(f'Section code {record.section_code} already exists.')


class TdsSectionSubsection(models.Model):
    _name = 'tds.section.subsection'
    _description = 'TDS Section Sub-sections'
    _order = 'subsection_code'

    section_id = fields.Many2one('tds.section', string='Section', required=True, ondelete='cascade')
    name = fields.Char(string='Sub-section Name', required=True)
    subsection_code = fields.Char(string='Sub-section Code', required=True)
    description = fields.Text(string='Description')
    max_limit = fields.Float(string='Maximum Limit')
    is_percentage_based = fields.Boolean(string='Percentage Based Calculation', default=False)
    percentage_of_income = fields.Float(string='Percentage of Income')


class TdsDeductionLine(models.Model):
    _name = 'tds.deduction.line'
    _description = 'TDS Deduction Line'

    calculation_id = fields.Many2one('tds.calculation', string='TDS Calculation', required=True, ondelete='cascade')
    section_id = fields.Many2one('tds.section', string='Section', required=True)
    subsection_id = fields.Many2one('tds.section.subsection', string='Sub-section')
    
    declared_amount = fields.Float(string='Declared Amount', required=True)
    proof_submitted = fields.Boolean(string='Proof Submitted', default=False)
    verified_amount = fields.Float(string='Verified Amount')
    allowed_amount = fields.Float(string='Allowed Amount', compute='_compute_allowed_amount', store=True)
    
    remarks = fields.Text(string='Remarks')
    attachment_ids = fields.Many2many('ir.attachment', string='Supporting Documents')
    
    @api.depends('declared_amount', 'verified_amount', 'proof_submitted', 'section_id')
    def _compute_allowed_amount(self):
        for record in self:
            if record.proof_submitted and record.verified_amount:
                base_amount = record.verified_amount
            else:
                base_amount = record.declared_amount
            
            # Apply section limits
            max_limit = getattr(record.section_id, 'max_deduction_limit', 0.0)
            is_unlimited = getattr(record.section_id, 'is_unlimited', False)
            
            if max_limit and not is_unlimited:
                record.allowed_amount = min(base_amount, max_limit)
            else:
                record.allowed_amount = base_amount
    
    @api.onchange('section_id')
    def _onchange_section_id(self):
        if self.section_id:
            self.subsection_id = False
