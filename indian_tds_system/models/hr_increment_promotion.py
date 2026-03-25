# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HrCareerUpdate(models.Model):
    _name = 'hr.career.update'
    _description = 'Career Update (Promotion & Increment)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'effective_date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    contract_id = fields.Many2one('hr.contract', string='Contract', required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', related='contract_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id', readonly=True)
    
    # Update Types
    is_promotion = fields.Boolean(string='Is Promotion?', default=True)
    is_increment = fields.Boolean(string='Is Salary Increment?', default=True)
    
    # Promotion Fields
    current_job_id = fields.Many2one('hr.job', string='Current Job Position', related='employee_id.job_id', readonly=True)
    new_job_id = fields.Many2one('hr.job', string='New Job Position', tracking=True)
    current_department_id = fields.Many2one('hr.department', string='Current Department', related='employee_id.department_id', readonly=True)
    new_department_id = fields.Many2one('hr.department', string='New Department', tracking=True)
    
    # Increment Fields
    current_wage = fields.Monetary(string='Current Wage', related='contract_id.wage', readonly=True, currency_field='currency_id')
    increment_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount')
    ], string='Increment Type', default='percentage', tracking=True)
    increment_amount = fields.Float(string='Increment Amount/Percentage', tracking=True)
    new_wage = fields.Monetary(string='New Wage', compute='_compute_new_wage', store=True, tracking=True, currency_field='currency_id')
    
    effective_date = fields.Date(string='Effective Date', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('applied', 'Applied'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    @api.depends('contract_id.wage', 'increment_type', 'increment_amount', 'is_increment')
    def _compute_new_wage(self):
        for record in self:
            if record.is_increment and record.contract_id:
                if record.increment_type == 'percentage':
                    record.new_wage = record.contract_id.wage * (1 + record.increment_amount / 100)
                else:
                    record.new_wage = record.contract_id.wage + record.increment_amount
            else:
                record.new_wage = record.contract_id.wage if record.contract_id else 0.0

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.career.update') or _('New')
        return super(HrCareerUpdate, self).create(vals)

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_apply(self):
        for record in self:
            if record.effective_date > fields.Date.today():
                raise ValidationError(_("Effective date must be today or in the past to apply."))
            
            # Apply Promotion
            if record.is_promotion:
                vals = {}
                if record.new_job_id:
                    vals['job_id'] = record.new_job_id.id
                if record.new_department_id:
                    vals['department_id'] = record.new_department_id.id
                if vals:
                    record.employee_id.write(vals)
            
            # Apply Increment
            if record.is_increment:
                record.contract_id.write({'wage': record.new_wage})
                # Trigger TDS Recalculation
                self._trigger_tds_recalculation(record.employee_id)
            
            record.state = 'applied'

    def _trigger_tds_recalculation(self, employee):
        tds_calc = self.env['tds.calculation'].search([
            ('employee_id', '=', employee.id),
            ('state', 'in', ['draft', 'calculated'])
        ], limit=1)
        if tds_calc:
            tds_calc.action_calculate()

