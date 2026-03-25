# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class TdsQuarterlyReturn(models.Model):
    _name = 'tds.quarterly.return'
    _description = 'TDS Quarterly Return (24Q)'
    _order = 'financial_year desc, quarter desc'
    _rec_name = 'return_name'

    # Basic Information
    return_name = fields.Char(string='Return Name', compute='_compute_return_name', store=True)
    financial_year = fields.Char(string='Financial Year', required=True)
    quarter = fields.Selection([
        ('q1', 'Q1 (Apr-Jun)'),
        ('q2', 'Q2 (Jul-Sep)'),
        ('q3', 'Q3 (Oct-Dec)'),
        ('q4', 'Q4 (Jan-Mar)')
    ], string='Quarter', required=True)

    # Period Dates
    period_from = fields.Date(string='Period From', required=True)
    period_to = fields.Date(string='Period To', required=True)

    # Company Information
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    company_pan = fields.Char(string='Company PAN', related='company_id.vat', store=True)
    company_tan = fields.Char(string='Company TAN', related='company_id.tan_number', store=True)

    # Return Details
    return_line_ids = fields.One2many('tds.quarterly.return.line', 'return_id', string='Return Lines')
    challan_ids = fields.Many2many('tds.challan', string='Related Challans')

    # Summary
    total_salary_paid = fields.Float(string='Total Salary Paid', compute='_compute_summary', store=True)
    total_tds_deducted = fields.Float(string='Total TDS Deducted', compute='_compute_summary', store=True)
    total_tds_deposited = fields.Float(string='Total TDS Deposited', compute='_compute_summary', store=True)

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('filed', 'Filed'),
        ('acknowledged', 'Acknowledged')
    ], string='Status', default='draft')

    # Filing Information
    filing_date = fields.Date(string='Filing Date')
    acknowledgment_number = fields.Char(string='Acknowledgment Number')

    @api.depends('financial_year', 'quarter')
    def _compute_return_name(self):
        for record in self:
            record.return_name = f"24Q - {record.financial_year} - {record.quarter.upper() if record.quarter else ''}"

    @api.depends('return_line_ids.salary_paid', 'return_line_ids.tds_deducted', 'challan_ids.total_tax_deposited')
    def _compute_summary(self):
        for record in self:
            record.total_salary_paid = sum(record.return_line_ids.mapped('salary_paid'))
            record.total_tds_deducted = sum(record.return_line_ids.mapped('tds_deducted'))
            record.total_tds_deposited = sum(record.challan_ids.mapped('total_tax_deposited'))

    def action_generate_return(self):
        """Generate quarterly return data"""
        self.ensure_one()

        # Clear existing lines
        self.return_line_ids.unlink()

        # Find all TDS calculations for the period
        calculations = self.env['tds.calculation'].search([
            ('date_from', '>=', self.period_from),
            ('date_to', '<=', self.period_to),
            ('state', 'in', ['approved', 'locked'])
        ])

        return_lines = []
        for calc in calculations:
            return_lines.append({
                'return_id': self.id,
                'employee_id': calc.employee_id.id,
                'employee_pan': calc.employee_id.pan_number,
                'salary_paid': calc.annual_salary,
                'tds_deducted': calc.total_tax_liability,
                'calculation_id': calc.id,
            })

        self.env['tds.quarterly.return.line'].create(return_lines)
        self.state = 'generated'
        return True

    def action_file_return(self):
        """File the quarterly return"""
        self.ensure_one()
        if self.state != 'generated':
            raise UserError('Return must be generated before filing.')

        self.state = 'filed'
        self.filing_date = fields.Date.today()
        return True


class TdsQuarterlyReturnLine(models.Model):
    _name = 'tds.quarterly.return.line'
    _description = 'TDS Quarterly Return Line'

    return_id = fields.Many2one('tds.quarterly.return', string='Return', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    employee_pan = fields.Char(string='Employee PAN')
    salary_paid = fields.Float(string='Salary Paid')
    tds_deducted = fields.Float(string='TDS Deducted')
    calculation_id = fields.Many2one('tds.calculation', string='TDS Calculation')
