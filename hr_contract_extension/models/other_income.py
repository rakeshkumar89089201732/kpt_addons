from odoo import models, fields, api
from odoo.exceptions import ValidationError


class OtherIncomeLine(models.Model):
    _name = 'other.income.line'
    _description = 'Other Income Line'
    _order = 'income_type, id'

    hr_tds_id = fields.Many2one('hr.tds', string='TDS Record', required=True, ondelete='cascade')
    income_type = fields.Selection([
        ('house_property', 'Income from House Property'),
        ('interest', 'Interest Income (Bank/FD/Savings)'),
        ('capital_gains_st', 'Short Term Capital Gains'),
        ('capital_gains_lt', 'Long Term Capital Gains'),
        ('dividend', 'Dividend Income'),
        ('business', 'Income from Business/Profession'),
        ('other_sources', 'Income from Other Sources')
    ], string='Income Type', required=True, help='Type of other income')
    income_amount = fields.Float('Income Amount', required=True, help='Total income amount for this type')
    description = fields.Text('Description', help='Details about this income source')
    is_taxable = fields.Boolean('Taxable', default=True, help='Whether this income is taxable')
    tax_exemption_amount = fields.Float('Tax Exemption Amount', help='Amount exempt from tax (if applicable)')
    net_taxable_amount = fields.Float('Net Taxable Amount', compute='_compute_net_taxable_amount', store=True, help='Income amount minus exemptions')

    @api.depends('income_amount', 'tax_exemption_amount', 'is_taxable')
    def _compute_net_taxable_amount(self):
        for line in self:
            if line.is_taxable:
                line.net_taxable_amount = max(line.income_amount - line.tax_exemption_amount, 0)
            else:
                line.net_taxable_amount = 0

    @api.constrains('income_amount', 'tax_exemption_amount')
    def _check_amounts(self):
        for line in self:
            if line.income_amount < 0:
                raise ValidationError('Income amount cannot be negative.')
            if line.tax_exemption_amount < 0:
                raise ValidationError('Tax exemption amount cannot be negative.')
            if line.tax_exemption_amount > line.income_amount:
                raise ValidationError('Tax exemption amount cannot exceed income amount.')
