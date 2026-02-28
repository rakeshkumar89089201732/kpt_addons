from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta


class SalaryIncrementLine(models.Model):
    _name = 'salary.increment.line'
    _description = 'Salary Increment Line'
    _order = 'effective_from'

    hr_tds_id = fields.Many2one('hr.tds', string='TDS Record', required=True, ondelete='cascade')
    line_type = fields.Selection([
        ('monthly', 'Monthly Salary (Period Based)'),
        ('one_time', 'One-Time Amount (Bonus/Commission/Arrear)'),
    ], string='Line Type', default='monthly', required=True)
    effective_from = fields.Date('Effective From', required=True, help='Date from which this salary is effective')
    effective_to = fields.Date('Effective To', help='Date until which this salary is effective')
    monthly_gross = fields.Float('Monthly Gross Salary', help='Gross salary per month for this period')
    one_time_amount = fields.Float('One-Time Amount', help='Single taxable amount (bonus/commission/arrear) within FY')
    one_time_tds = fields.Float('One-Time TDS', help='Additional TDS to deduct for this one-time payment month (added on top of regular monthly TDS)')
    one_time_tds_suggested = fields.Float('Suggested One-Time TDS', compute='_compute_one_time_tds_suggested', store=False, help='Auto-suggested additional TDS based on incremental tax impact of this one-time amount')
    increment_reason = fields.Selection([
        ('joining', 'Joining Salary'),
        ('increment', 'Annual Increment'),
        ('promotion', 'Promotion'),
        ('arrear', 'Arrear Payment'),
        ('bonus', 'Bonus/Variable Pay'),
        ('other', 'Other')
    ], string='Reason', default='increment', required=True)
    remarks = fields.Text('Remarks')
    number_of_months = fields.Float('Number of Months', compute='_compute_number_of_months', store=True, help='Number of months in this period')
    total_for_period = fields.Float('Total for Period', compute='_compute_total_for_period', store=True, help='Total salary for this line')

    @api.depends('effective_from', 'effective_to', 'line_type')
    def _compute_number_of_months(self):
        for line in self:
            if line.line_type == 'one_time':
                line.number_of_months = 0
            elif line.effective_from and line.effective_to:
                delta = relativedelta(line.effective_to, line.effective_from)
                months = (delta.years * 12) + delta.months
                if line.effective_to.day >= line.effective_from.day:
                    months += 1
                line.number_of_months = max(months, 0)
            else:
                line.number_of_months = 0

    @api.depends('line_type', 'monthly_gross', 'number_of_months', 'one_time_amount')
    def _compute_total_for_period(self):
        for line in self:
            if line.line_type == 'one_time':
                line.total_for_period = line.one_time_amount or 0.0
            else:
                line.total_for_period = (line.monthly_gross or 0.0) * (line.number_of_months or 0.0)

    @api.depends('line_type', 'one_time_amount', 'hr_tds_id', 'hr_tds_id.taxable_amount', 'hr_tds_id.tax_regime_slab')
    def _compute_one_time_tds_suggested(self):
        for line in self:
            suggested = 0.0
            if line.line_type != 'one_time':
                line.one_time_tds_suggested = 0.0
                continue
            if not line.hr_tds_id or not line.hr_tds_id.tax_regime_slab:
                line.one_time_tds_suggested = 0.0
                continue
            one_time_amt = float(line.one_time_amount or 0.0)
            if one_time_amt <= 0.0:
                line.one_time_tds_suggested = 0.0
                continue

            # Compute incremental tax-with-cess caused by this one-time amount.
            # annual taxable already includes all one-time amounts; so compare current taxable
            # vs taxable reduced by this line's amount.
            tds = line.hr_tds_id
            taxable_with = float(tds.taxable_amount or 0.0)
            taxable_without = max(taxable_with - one_time_amt, 0.0)
            try:
                _, _, tax_with_cess_with, _ = tds._get_tax_amounts_from_slabs(taxable_with)
                _, _, tax_with_cess_without, _ = tds._get_tax_amounts_from_slabs(taxable_without)
                suggested = max(float(tax_with_cess_with or 0.0) - float(tax_with_cess_without or 0.0), 0.0)
            except Exception:
                suggested = 0.0

            line.one_time_tds_suggested = suggested

    @api.constrains('line_type', 'effective_from', 'effective_to', 'monthly_gross', 'one_time_amount')
    def _check_dates(self):
        for line in self:
            if line.effective_from and line.effective_to and line.effective_from > line.effective_to:
                raise ValidationError('Effective From date must be before Effective To date.')

            if line.line_type == 'monthly':
                if not line.effective_to:
                    raise ValidationError('Effective To is required for Monthly Salary lines.')
                if (line.monthly_gross or 0.0) <= 0:
                    raise ValidationError('Monthly gross salary must be greater than 0 for Monthly Salary lines.')

            if line.line_type == 'one_time':
                if (line.one_time_amount or 0.0) <= 0:
                    raise ValidationError('One-time amount must be greater than 0 for One-Time Amount lines.')

                if (line.one_time_tds or 0.0) < 0:
                    raise ValidationError('One-time TDS cannot be negative.')

            if line.line_type == 'monthly' and (line.monthly_gross or 0.0) < 0:
                raise ValidationError('Monthly gross salary cannot be negative.')
            if line.line_type == 'one_time' and (line.one_time_amount or 0.0) < 0:
                raise ValidationError('One-time amount cannot be negative.')

            # Ensure salary increment periods don't go outside FY or before current contract start
            if line.hr_tds_id:
                tds = line.hr_tds_id
                if tds.tds_from_date and line.effective_from and line.effective_from < tds.tds_from_date:
                    raise ValidationError('Salary period cannot start before the TDS From Date (FY start).')
                if tds.tds_to_date and line.effective_to and line.effective_to > tds.tds_to_date:
                    raise ValidationError('Salary period cannot end after the TDS To Date (FY end).')

                # --- Odoo 13/17 customization note ---
                # Previously, salary increment lines were restricted to the current contract period only.
                # This blocks auto-sync when we build increment lines from multiple employee contracts
                # within the same FY (open + closed), which is required to reflect mid-year increments.
                # FY boundary checks above remain authoritative.
                #
                # if line.line_type == 'monthly' and tds.hr_contract_id and tds.hr_contract_id.date_start and line.effective_from and line.effective_from < tds.hr_contract_id.date_start:
                #     raise ValidationError(
                #         'Salary increment lines are for the current employer period only. '
                #         'For income before the current contract start, use the Previous Employer Salary field.'
                #     )
            
            # Check for overlapping periods within the same TDS record (only for monthly lines).
            # One-time amounts can be paid within an existing salary period.
            if line.line_type == 'monthly' and line.hr_tds_id:
                overlapping = self.search([
                    ('hr_tds_id', '=', line.hr_tds_id.id),
                    ('id', '!=', line.id),
                    ('line_type', '=', 'monthly'),
                    '|',
                    '&', ('effective_from', '<=', line.effective_from), ('effective_to', '>=', line.effective_from),
                    '&', ('effective_from', '<=', line.effective_to), ('effective_to', '>=', line.effective_to)
                ])
                if overlapping:
                    raise ValidationError('Salary periods cannot overlap. Please check the dates.')

    @api.onchange('effective_from')
    def _onchange_effective_from(self):
        """Auto-set effective_to to end of FY if not set"""
        if self.effective_from and not self.effective_to and self.hr_tds_id:
            self.effective_to = self.hr_tds_id.tds_to_date

    @api.onchange('line_type', 'effective_from')
    def _onchange_line_type(self):
        for line in self:
            if line.line_type == 'one_time' and line.effective_from:
                line.effective_to = line.effective_from

    @api.onchange('one_time_amount', 'line_type', 'hr_tds_id')
    def _onchange_one_time_amount_auto_tds(self):
        for line in self:
            if line.line_type != 'one_time':
                continue
            # Auto-fill only when user has not entered anything yet.
            if (line.one_time_tds or 0.0) == 0.0 and (line.one_time_tds_suggested or 0.0) > 0.0:
                line.one_time_tds = line.one_time_tds_suggested

    def action_open_paid_tds_period_wizard(self):
        self.ensure_one()
        if not self.hr_tds_id:
            raise UserError('TDS record not found.')
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.tds.paid.period.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_hr_tds_id': self.hr_tds_id.id,
                'default_period_from': self.effective_from,
                'default_period_to': self.effective_to or self.effective_from,
            },
        }
