from stdnum.au.acn import to_abn

from odoo import _, models, api, fields
from collections import defaultdict
import math
import itertools
from datetime import datetime, timedelta, date
import json
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta


class HrTDSPaidPeriod(models.Model):
    _name = 'hr.tds.paid.period'
    _description = 'TDS Paid Period (Current Employer)'
    _order = 'period_from'

    hr_tds_id = fields.Many2one('hr.tds', string='TDS Record', required=True, ondelete='cascade')
    period_from = fields.Date(string='Period From', required=True)
    period_to = fields.Date(string='Period To', required=True)
    amount = fields.Float(string='TDS Paid Amount', required=True)
    remarks = fields.Char(string='Remarks')

    @api.constrains('period_from', 'period_to', 'amount')
    def _check_paid_period(self):
        for rec in self:
            if rec.period_from and rec.period_to and rec.period_from > rec.period_to:
                raise ValidationError(_('Period From must be before Period To.'))
            if (rec.amount or 0.0) <= 0.0:
                raise ValidationError(_('TDS Paid Amount must be greater than 0.'))
            if rec.hr_tds_id and rec.hr_tds_id.tds_from_date and rec.period_from and rec.period_from < rec.hr_tds_id.tds_from_date:
                raise ValidationError(_('Paid TDS Period cannot start before the TDS From Date (FY start).'))
            if rec.hr_tds_id and rec.hr_tds_id.tds_to_date and rec.period_to and rec.period_to > rec.hr_tds_id.tds_to_date:
                raise ValidationError(_('Paid TDS Period cannot end after the TDS To Date (FY end).'))


class HrTDSPaidPeriodWizard(models.TransientModel):
    _name = 'hr.tds.paid.period.wizard'
    _description = 'Paid TDS Period Wizard'

    hr_tds_id = fields.Many2one('hr.tds', string='TDS Record', required=True)
    period_from = fields.Date(string='Period From', required=True)
    period_to = fields.Date(string='Period To', required=True)
    amount = fields.Float(string='TDS Paid Amount')
    remarks = fields.Char(string='Remarks')
    line_ids = fields.One2many('hr.tds.paid.period.wizard.line', 'wizard_id', string='Month Wise TDS')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        hr_tds_id = res.get('hr_tds_id')
        period_from = res.get('period_from')
        period_to = res.get('period_to')
        if period_from and period_to and period_from <= period_to and not res.get('line_ids'):
            months = []
            cur = period_from.replace(day=1)
            end = period_to.replace(day=1)
            while cur <= end:
                months.append(cur)
                cur += relativedelta(months=1)

            existing_amount_by_month = {}
            if hr_tds_id and months:
                existing = self.env['hr.tds.paid.month'].search([
                    ('hr_tds_id', '=', hr_tds_id),
                    ('month_date', 'in', months),
                ])
                existing_amount_by_month = {e.month_date: float(e.amount or 0.0) for e in existing if e.month_date}

            res['line_ids'] = [(0, 0, {
                'month_date': m,
                'month_label': m.strftime('%B %Y'),
                'amount': existing_amount_by_month.get(m, 0.0),
            }) for m in months]
        return res

    @api.onchange('period_from', 'period_to')
    def _onchange_period_dates_generate_month_lines(self):
        for wiz in self:
            if not wiz.period_from or not wiz.period_to or wiz.period_from > wiz.period_to:
                wiz.line_ids = [(5, 0, 0)]
                continue

            months = []
            cur = wiz.period_from.replace(day=1)
            end = wiz.period_to.replace(day=1)
            while cur <= end:
                months.append(cur)
                cur += relativedelta(months=1)

            existing_amount_by_month = {}
            if wiz.hr_tds_id and months:
                existing = self.env['hr.tds.paid.month'].search([
                    ('hr_tds_id', '=', wiz.hr_tds_id.id),
                    ('month_date', 'in', months),
                ])
                existing_amount_by_month = {e.month_date: float(e.amount or 0.0) for e in existing if e.month_date}

            cmds = [(5, 0, 0)]
            for m in months:
                cmds.append((0, 0, {
                    'month_date': m,
                    'month_label': m.strftime('%B %Y'),
                    'amount': existing_amount_by_month.get(m, 0.0),
                }))
            wiz.line_ids = cmds

    def action_confirm(self):
        self.ensure_one()
        if not self.hr_tds_id:
            raise UserError(_('TDS record not found.'))
        if self.period_from and self.period_to and self.period_from > self.period_to:
            raise UserError(_('Period From must be before Period To.'))
        # Prefer month-wise amounts if period month lines exist.
        # Important: allowing "clear" operations (set to 0) must delete stored paid-month rows.
        has_month_grid = bool(self.line_ids.filtered(lambda l: l.month_date))
        has_any_positive_month = bool(self.line_ids.filtered(lambda l: l.month_date and (l.amount or 0.0) > 0.0))

        if has_month_grid:
            months_in_period = []
            if self.period_from and self.period_to and self.period_from <= self.period_to:
                cur = self.period_from.replace(day=1)
                end = self.period_to.replace(day=1)
                while cur <= end:
                    months_in_period.append(cur)
                    cur += relativedelta(months=1)

            # Delete any matching period record for this exact range to avoid leftover allocations.
            self.env['hr.tds.paid.period'].search([
                ('hr_tds_id', '=', self.hr_tds_id.id),
                ('period_from', '=', self.period_from),
                ('period_to', '=', self.period_to),
            ]).unlink()

            for l in self.line_ids.filtered(lambda ln: ln.month_date):
                existing = self.env['hr.tds.paid.month'].search([
                    ('hr_tds_id', '=', self.hr_tds_id.id),
                    ('month_date', '=', l.month_date),
                ], limit=1)

                if (l.amount or 0.0) > 0.0:
                    vals = {
                        'hr_tds_id': self.hr_tds_id.id,
                        'month_date': l.month_date,
                        'amount': l.amount,
                        'remarks': self.remarks,
                    }
                    if existing:
                        existing.write(vals)
                    else:
                        self.env['hr.tds.paid.month'].create(vals)
                else:
                    # Clear saved paid TDS for this month (amount must be > 0 due to constraint, so unlink).
                    if existing:
                        existing.unlink()

            # If the user cleared all months (all zeros), do not require total amount.
            # This lets the user remove previously entered paid TDS.
            if not has_any_positive_month and (self.amount or 0.0) > 0.0:
                # If they also entered a period total, store it as period record.
                self.env['hr.tds.paid.period'].create({
                    'hr_tds_id': self.hr_tds_id.id,
                    'period_from': self.period_from,
                    'period_to': self.period_to,
                    'amount': self.amount,
                    'remarks': self.remarks,
                })
        else:
            if (self.amount or 0.0) <= 0.0:
                raise UserError(_('Enter either Month Wise TDS amounts or a total TDS Paid Amount.'))
            self.env['hr.tds.paid.period'].create({
                'hr_tds_id': self.hr_tds_id.id,
                'period_from': self.period_from,
                'period_to': self.period_to,
                'amount': self.amount,
                'remarks': self.remarks,
            })

        if not self.hr_tds_id.use_paid_tds_periods:
            self.hr_tds_id.use_paid_tds_periods = True
        return {'type': 'ir.actions.act_window_close'}


class HrTDSPaidPeriodWizardLine(models.TransientModel):
    _name = 'hr.tds.paid.period.wizard.line'
    _description = 'Paid TDS Period Wizard Line'
    _order = 'month_date'

    wizard_id = fields.Many2one('hr.tds.paid.period.wizard', required=True, ondelete='cascade')
    month_date = fields.Date(string='Month', required=True)
    month_label = fields.Char(string='Month', readonly=True)
    amount = fields.Float(string='TDS Paid Amount')


class HrTDSPaidMonth(models.Model):
    _name = 'hr.tds.paid.month'
    _description = 'TDS Paid Month (Current Employer)'
    _order = 'month_date'

    hr_tds_id = fields.Many2one('hr.tds', string='TDS Record', required=True, ondelete='cascade')
    month_date = fields.Date(string='Month', required=True)
    amount = fields.Float(string='TDS Paid Amount', required=True)
    remarks = fields.Char(string='Remarks')

    _sql_constraints = [
        ('unique_paid_month_per_tds', 'unique(hr_tds_id, month_date)', 'Month Wise TDS for this month already exists.'),
    ]

    @api.constrains('month_date', 'amount')
    def _check_paid_month(self):
        for rec in self:
            if (rec.amount or 0.0) <= 0.0:
                raise ValidationError(_('TDS Paid Amount must be greater than 0.'))
            if rec.hr_tds_id and rec.hr_tds_id.tds_from_date and rec.month_date and rec.month_date < rec.hr_tds_id.tds_from_date:
                raise ValidationError(_('Paid TDS month cannot be before the TDS From Date (FY start).'))
            if rec.hr_tds_id and rec.hr_tds_id.tds_to_date and rec.month_date and rec.month_date > rec.hr_tds_id.tds_to_date:
                raise ValidationError(_('Paid TDS month cannot be after the TDS To Date (FY end).'))
class HrTDS(models.Model):
    _name = 'hr.tds'
    _description = 'HR TDS'

    def _get_current_employer_start_date(self, fy_start, fy_end):
        self.ensure_one()
        employee = self.hr_employee_id or (self.hr_contract_id.employee_id if self.hr_contract_id else False)
        if not employee or not fy_start or not fy_end:
            return (self.hr_contract_id.date_start if self.hr_contract_id and self.hr_contract_id.date_start else fy_start)

        fy_contracts = self.env['hr.contract'].search([
            ('employee_id', '=', employee.id),
            ('state', 'in', ['open', 'close']),
            ('date_start', '<=', fy_end),
            '|',
            ('date_end', '=', False),
            ('date_end', '>=', fy_start),
        ], order='date_start')
        if fy_contracts:
            starts = [c.date_start for c in fy_contracts if c.date_start]
            if starts:
                return max(min(starts), fy_start)
        return (self.hr_contract_id.date_start if self.hr_contract_id and self.hr_contract_id.date_start else fy_start)

    def get_fy_range(self):
        today = date.today()
        year = today.year
        if today.month < 4:  # Jan/Feb/Mar = previous FY
            year -= 1
        return f'{year}-04-01', f'{year + 1}-03-31'
    
    def _default_tds_from_date(self):
        """Default TDS from date - always FY start (April 1)"""
        return self.get_fy_range()[0]
    
    def _default_tds_to_date(self):
        """Default TDS to date - always FY end (March 31)"""
        return self.get_fy_range()[1]

    hr_contract_id = fields.Many2one('hr.contract', string='Contract')
    hr_employee_id = fields.Many2one('hr.employee', string='Employee', copy=False)
    salary_increment_ids = fields.One2many('salary.increment.line', 'hr_tds_id', string='Salary Increments', help='Track multiple salary changes during the financial year')
    use_salary_increments = fields.Boolean('Use Salary Increments', default=False, help='Enable to track multiple salary changes during FY')

    use_paid_tds_periods = fields.Boolean('Use Paid TDS Periods', default=False)
    paid_tds_period_ids = fields.One2many('hr.tds.paid.period', 'hr_tds_id', string='TDS Paid (Period Wise)')
    paid_tds_month_ids = fields.One2many('hr.tds.paid.month', 'hr_tds_id', string='TDS Paid (Month Wise)')

    def action_open_paid_tds_period_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.tds.paid.period.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_hr_tds_id': self.id,
                'default_period_from': self.tds_from_date,
                'default_period_to': self.tds_to_date,
            },
        }
    
    def action_open_regime_comparison(self):
        """Open wizard to compare Old vs New tax regime calculations"""
        self.ensure_one()

        fy_start = self.tds_from_date
        fy_end = self.tds_to_date
        if not fy_start or not fy_end:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Tax Regime Comparison',
                'res_model': 'tds.regime.comparison.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_hr_tds_id': self.id,
                },
            }

        Slab = self.env['tax.slab']
        old_slab = Slab.search([
            ('tax_regime_type', '=', 'old'),
            ('date_start', '<=', fy_end),
            ('date_end', '>=', fy_start),
            ('active', '=', True),
        ], order='date_start desc', limit=1)
        new_slab = Slab.search([
            ('tax_regime_type', '=', 'new'),
            ('date_start', '<=', fy_end),
            ('date_end', '>=', fy_start),
            ('active', '=', True),
        ], order='date_start desc', limit=1)

        # If one of the slabs is missing, guide the user to configure it instead of raising a blocking error.
        if not old_slab or not new_slab:
            missing_type = 'old' if not old_slab else 'new'
            return {
                'type': 'ir.actions.act_window',
                'name': 'Tax Slabs',
                'res_model': 'tax.slab',
                'view_mode': 'tree,form',
                'target': 'current',
                'domain': [
                    ('date_start', '<=', fy_end),
                    ('date_end', '>=', fy_start),
                    ('active', '=', True),
                ],
                'context': {
                    **self.env.context,
                    'default_tax_regime_type': missing_type,
                    'default_date_start': fy_start,
                    'default_date_end': fy_end,
                    'search_default_tax_regime_type': missing_type,
                },
            }

        return {
            'type': 'ir.actions.act_window',
            'name': 'Tax Regime Comparison',
            'res_model': 'tds.regime.comparison.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_hr_tds_id': self.id,
            },
        }
    current_ctc = fields.Float(string='Current CTC', compute='_compute_current_ctc', store=True)
    annual_salary = fields.Float(string='Annual Income', compute='_compute_annual_salary', store=True, readonly=False, digits=(16, 0))
    other_income_ids = fields.One2many('other.income.line', 'hr_tds_id', string='Other Income', help='Track income from sources other than salary')
    total_other_income = fields.Float('Total Other Income', compute='_compute_total_other_income', store=True, help='Sum of all other taxable income')
    total_deductions = fields.Float(string='Total Deductions', compute='_compute_total_deductions', store=True)
    taxable_amount = fields.Float(string='Taxable Amount', compute='_compute_tax_slab', store=True, digits=(16, 0))
    tax_payable = fields.Float(string='Tax Payable', digits=(16, 0))
    tax_payable_cess = fields.Float(string='Tax Payable Cess', digits=(16, 0))
    tax_round_off_amount = fields.Float(string='Tax Round Off', digits=(16, 0))
    tax_breakdown_html = fields.Html(string='Tax Breakdown', compute='_compute_tax_breakdown_html', sanitize=False, store=False)
    tax_regime_slab = fields.Many2one('tax.slab', string='Tax Slab', copy=False)
    tax_regime_type = fields.Selection(related='tax_regime_slab.tax_regime_type', string='Regime Type', store=True, readonly=True)
    tax_regime_allowed_scheme_ids = fields.Many2many(
        related='tax_regime_slab.allowed_scheme_ids',
        string='Allowed Schemes (from Tax Slab)',
        readonly=True,
    )
    available_scheme_ids = fields.Many2many(
        'tds.section.scheme',
        compute='_compute_available_scheme_ids',
        store=False,
        help='Technical: schemes allowed for selection based on the selected Tax Slab configuration (fallback to regime applicability).'
    )
    available_section_ids = fields.Many2many(
        'tds.section',
        compute='_compute_available_section_ids',
        store=False,
        help='Technical: sections allowed for selection based on available_scheme_ids.'
    )
    has_slab_scheme_config = fields.Boolean(
        compute='_compute_has_slab_scheme_config',
        store=False,
        help='Technical field used to decide whether to filter schemes by Tax Slab configuration.'
    )
    deduction_ids = fields.One2many('deduction.description', 'hr_tds_id')
    grouped_deductions_html = fields.Html(compute="_compute_grouped_deductions_html", sanitize=False, store=False)
    deduction_summary_html = fields.Html(compute='_compute_deduction_summary_html', sanitize=False, store=False)
    deduction_cache_old = fields.Text()
    deduction_cache_new = fields.Text()
    prepaid_tds = fields.Float('Prepaid TDS')
    tax_pay_ref = fields.Float('Tax Payable/Refundable', compute='_compute_tax_pay_ref', store=True, readonly=False, digits=(16, 0))
    tds_deduction_month = fields.Float(string='TDS Deduction Per month', compute='_compute_monthly_tds', store=True, readonly=False, digits=(16, 0))
    tds_deduction_month_cess = fields.Float(string='TDS Deduction Per month Cess', compute='_compute_monthly_tds', store=True, readonly=False, digits=(16, 0))
    month_ids = fields.One2many('month.wise.tds', 'hr_tds_id', store=True, )
    monthly_breakdown_html = fields.Html(compute='_compute_monthly_breakdown_html', sanitize=False, store=False)
    tds_from_month = fields.Char('TDS From', compute='_compute_month_ids', store=True)
    tds_to_month = fields.Char('TDS To', compute='_compute_month_ids', store=True)
    is_tds_payslip = fields.Boolean(string="Appears On Payslip", default=False)
    prorate_by_attendance = fields.Boolean(string='Prorate TDS by Attendance', default=True, help='When enabled, distribute current-employer monthly TDS proportionally to monthly attendance (present weekdays) within FY months. Falls back to equal split if attendance is unavailable.')

    tds_from_date = fields.Date('TDS From Date', default=_default_tds_from_date, required=True)
    tds_to_date = fields.Date('TDS To Date', default=_default_tds_to_date, required=True)

    # --- 24Q Critical Fields (Phase 1) ---
    perquisites_17_2 = fields.Float('Perquisites u/s 17(2)', help='Value of perquisites under section 17(2)')
    profits_17_3 = fields.Float('Profits in lieu u/s 17(3)', help='Profits in lieu of salary under section 17(3)')
    previous_employer_company_name = fields.Char('Previous Employer Company Name', help='Previous employer company name (if employee switched mid-year)')
    previous_employer_taxable = fields.Float('Previous Employer Taxable', help='Reported taxable amount from previous employer(s)')
    previous_employer_from_date = fields.Date('Previous Employer From Date')
    previous_employer_to_date = fields.Date('Previous Employer To Date')
    standard_deduction_16_ii = fields.Float('Standard Deduction u/s 16(ii)', default=0.0, help='Standard deduction under section 16(ii)')
    rebate_87a = fields.Float('Rebate u/s 87A', help='Rebate under section 87A (if applicable)')
    surcharge = fields.Float('Surcharge', help='Surcharge on income tax')
    health_education_cess = fields.Float('Health & Education Cess', help='Health and education cess (4% of tax + surcharge)', digits=(16, 0))
    new_tax_regime_opted = fields.Boolean('New Tax Regime (115BAC) Opted?', help='Whether employee opted for new tax regime u/s 115BAC')
    gross_total_income = fields.Float('Gross Total Income', compute='_compute_gross_total_income', store=False, digits=(16, 0))
    income_chargeable_salaries = fields.Float('Income Chargeable (Salaries)', compute='_compute_income_chargeable_salaries', store=True, help='Income chargeable under the head Salaries', digits=(16, 0))
    
    # --- Tax Regime Comparison Fields ---
    old_regime_tax_payable = fields.Float('Old Regime Tax', readonly=True, digits=(16, 0), help='Calculated tax under old regime')
    new_regime_tax_payable = fields.Float('New Regime Tax', readonly=True, digits=(16, 0), help='Calculated tax under new regime')
    recommended_regime = fields.Selection([
        ('old', 'Old Tax Regime'),
        ('new', 'New Tax Regime'),
    ], string='Recommended Regime', readonly=True, help='Regime with lower tax liability')
    tax_savings_amount = fields.Float('Potential Savings', readonly=True, digits=(16, 0), help='Difference between old and new regime tax')
    
    # Deduction totals per regime (for display purposes)
    old_regime_total_deductions = fields.Float('Old Regime Deductions', compute='_compute_regime_deduction_totals', store=False, help='Total deductions claimed under old regime')
    new_regime_total_deductions = fields.Float('New Regime Deductions', compute='_compute_regime_deduction_totals', store=False, help='Total deductions claimed under new regime')

    # --- Section 10 Exemptions ---
    travel_concession_10_5 = fields.Float('Travel Concession u/s 10(5)', help='Travel concession or assistance under section 10(5)')
    gratuity_10_10 = fields.Float('Gratuity u/s 10(10)', help='Death-cum-retirement gratuity under section 10(10)')
    commuted_pension_10_10a = fields.Float('Commuted Pension u/s 10(10A)', help='Commuted value of pension under section 10(10A)')
    leave_salary_10_10aa = fields.Float('Leave Salary u/s 10(10AA)', help='Cash equivalent of leave salary encashment under section 10(10AA)')
    other_exemptions_10 = fields.Float('Other Exemptions u/s 10', help='Amount of any other exemption under section 10')
    total_exemptions_10 = fields.Float('Total Exemptions u/s 10', compute='_compute_total_exemptions_10', store=True, help='Total amount of exemption claimed under section 10')



    #calculation of HRA Fields
    rent_payment_ids = fields.One2many('rent.payment.line', 'hr_tds_id', string='Rent Payments', help='Track multiple rent periods during the financial year')
    use_multiple_rent_periods = fields.Boolean('Use Multiple Rent Periods', default=False, help='Enable to track rent changes during FY')
    total_rent_paid = fields.Float('Total Rent Paid', compute='_compute_total_rent_paid', store=True, help='Sum of all rent payments')
    total_hra_exemption = fields.Float('Total HRA Exemption', compute='_compute_total_hra_exemption', store=True, help='Sum of HRA exemptions from all rent periods')

    basic_salary = fields.Float('Basic Salary')
    actual_rental_paid = fields.Float('Actual Rent Paid')
    hra_received = fields.Float('HRA Received')
    rent_excess_per = fields.Float('Rent Paid Excess %')
    rent_exempt_amt = fields.Float('Exempt Amt', compute='_compute_rent_exempt', store=True)
    hra_per = fields.Float('HRA %')
    hra_amt = fields.Float('HRA Amt', compute='_compute_hra_amt', store=True)
    final_hra_amt = fields.Float('Final HRA Amt', compute='_compute_final_hra', store=True)


    # @api.onchange("tds_from_date")
    # def _onchange_tds_from_date(self):
    #     """Automatically set name based on date_start"""
    #     if self.tds_from_date:
    #         year = self.tds_from_date.year
    #         self.tds_to_date = self.tds_from_date.replace(year=year + 1) - timedelta(days=1)


    # @api.constrains('tds_from_date')
    # def _check_tds_start_against_payslips(self):
    #     for record in self:
    #         if record.tds_from_date:
    #             # Search for payslips generated for this employee on or after the selected start date
    #             payslips = self.env['hr.payslip'].search([
    #                 ('employee_id', '=', record.hr_employee_id.id),
    #                 ('state', 'in', ['done', 'paid']),
    #                 ('date_from', '>=', record._origin.tds_from_date),
    #             ])
    #             if payslips:
    #                 raise ValidationError(
    #                     "Cannot change TDS From Date to a period where payslips have already been generated."
    #                 )


    @api.depends('hr_contract_id', 'hr_contract_id.gross', 'hr_contract_id.wage')
    def _compute_current_ctc(self):
        for tds in self:
            if not tds.hr_contract_id:
                tds.current_ctc = 0.0
                continue
            contract = tds.hr_contract_id
            monthly_salary = contract.gross if contract.gross else contract.wage
            tds.current_ctc = (monthly_salary or 0.0) * 12


    @api.depends('annual_salary', 'previous_employer_taxable', 'perquisites_17_2', 'profits_17_3', 'total_other_income')
    def _compute_gross_total_income(self):
        for tds in self:
            tds.gross_total_income = float(
                (tds.annual_salary or 0.0)
                + (tds.previous_employer_taxable or 0.0)
                + (tds.perquisites_17_2 or 0.0)
                + (tds.profits_17_3 or 0.0)
                + (tds.total_other_income or 0.0)
            )


    @api.depends('hr_contract_id', 'hr_contract_id.gross', 'hr_contract_id.wage', 'hr_contract_id.date_start', 'tds_from_date', 'tds_to_date', 'salary_increment_ids', 'salary_increment_ids.total_for_period', 'use_salary_increments', 'hr_employee_id')
    def _compute_annual_salary(self):
        """
        Calculate annual salary for current employer considering all contracts in the FY.
        This handles mid-year salary increments via contract renewal:
        - If salary increment lines exist, use them (manual override).
        - Otherwise, sum salary from ALL employee contracts in current FY (expired + running).
        Example: Employee had contract A (100k/month, Apr-Oct), then contract B (120k/month, Nov-Mar).
        Annual salary = (100k * 7 months) + (120k * 5 months) = 1,300k
        """
        for tds in self:
            employee = tds.hr_employee_id or tds.hr_contract_id.employee_id

            def _month_bounds(d):
                ms = d.replace(day=1)
                me = ms + relativedelta(months=1, days=-1)
                return ms, me

            def _overlap_days(start_a, end_a, start_b, end_b):
                if not (start_a and end_a and start_b and end_b):
                    return 0
                s = max(start_a, start_b)
                e = min(end_a, end_b)
                if s > e:
                    return 0
                return (e - s).days + 1

            # Priority 1: Use salary increment lines when available (auto-filled from contracts)
            if tds.salary_increment_ids:
                if tds.tds_from_date and tds.tds_to_date:
                    fy_start = tds.tds_from_date
                    fy_end = tds.tds_to_date

                    total_salary = 0.0
                    probe = fy_start.replace(day=1)
                    while probe <= fy_end:
                        ms, me = _month_bounds(probe)
                        total_days = (me - ms).days + 1
                        month_total = 0.0
                        for line in tds.salary_increment_ids:
                            if line.line_type == 'one_time':
                                if line.effective_from and ms <= line.effective_from <= me:
                                    month_total += line.one_time_amount or 0.0
                                continue

                            line_start = max(line.effective_from or ms, ms, fy_start)
                            line_end = min(line.effective_to or me, me, fy_end)
                            od = _overlap_days(line_start, line_end, ms, me)
                            if od and total_days:
                                month_total += (line.monthly_gross or 0.0) * (float(od) / float(total_days))

                        total_salary += month_total
                        probe += relativedelta(months=1)

                    tds.annual_salary = float(total_salary)
                else:
                    tds.annual_salary = float(sum(tds.salary_increment_ids.mapped('total_for_period')))
            # Priority 2: Calculate from all employee contracts in current FY
            elif employee and tds.tds_from_date and tds.tds_to_date:
                fy_start = tds.tds_from_date
                fy_end = tds.tds_to_date
                
                # Find all contracts for this employee that overlap with current FY
                all_fy_contracts = self.env['hr.contract'].search([
                    ('employee_id', '=', employee.id),
                    ('state', 'in', ['open', 'close']),
                    '|',
                    '&', ('date_start', '>=', fy_start), ('date_start', '<=', fy_end),
                    '&', ('date_end', '>=', fy_start), ('date_end', '<=', fy_end),
                    '|',
                    '&', ('date_start', '<=', fy_start), ('date_end', '>=', fy_end),
                    '&', ('date_start', '<=', fy_start), ('date_end', '=', False),
                ], order='date_start')
                
                total_salary = 0.0
                for contract in all_fy_contracts:
                    monthly_salary = contract.gross if contract.gross else contract.wage
                    if not monthly_salary:
                        continue
                    
                    # Determine contract period within FY
                    contract_start = max(contract.date_start or fy_start, fy_start)
                    contract_end = min(contract.date_end or fy_end, fy_end)
                    
                    if contract_start <= contract_end:
                        probe = contract_start.replace(day=1)
                        while probe <= contract_end:
                            ms, me = _month_bounds(probe)
                            total_days = (me - ms).days + 1
                            line_start = max(contract_start, ms, fy_start)
                            line_end = min(contract_end, me, fy_end)
                            od = _overlap_days(line_start, line_end, ms, me)
                            if od and total_days:
                                total_salary += monthly_salary * (float(od) / float(total_days))
                            probe += relativedelta(months=1)
                
                tds.annual_salary = float(total_salary)
            elif not tds.annual_salary:
                tds.annual_salary = 0.0

    # --- Odoo 13 → 18 migration note ---
    # Autofill HRA inputs from the linked contract so the user does not have to retype.
    # basic_salary: annualized wage
    # hra_received: annualized house_rent_allowance
    def _sync_hra_from_contract(self):
        for tds in self:
            contract = tds.hr_contract_id
            if not contract:
                continue
            if not tds.basic_salary:
                tds.basic_salary = (contract.wage or 0.0) * 12
            if not tds.hra_received:
                tds.hra_received = (contract.house_rent_allowance or 0.0) * 12
            if not tds.hra_per:
                # Default to 40% unless the user sets a different percentage.
                tds.hra_per = 40.0
            if not tds.rent_excess_per:
                # Default statutory 10% threshold on salary
                tds.rent_excess_per = 10.0

    @api.onchange('hr_contract_id')
    def _onchange_hr_contract_id(self):
        """Autofill employee, HRA inputs and Tax Regime when contract changes."""
        if self.hr_contract_id:
            if not self.hr_employee_id and self.hr_contract_id.employee_id:
                self.hr_employee_id = self.hr_contract_id.employee_id
            if self.hr_contract_id.tax_regime_slab and not self.tax_regime_slab:
                self.tax_regime_slab = self.hr_contract_id.tax_regime_slab
        self._sync_hra_from_contract()
        self._compute_total_rent_paid()
        self._compute_total_hra_exemption()

    def _sync_salary_increments_from_contracts(self):
        """Populate salary increment lines from FY contracts when toggle is enabled.

        - Creates increment lines only if there are no existing lines (no deletions).
        - Uses all employee contracts overlapping the FY (draft/open/close).
        """
        SalaryIncrement = self.env['salary.increment.line']
        for tds in self:
            if tds.salary_increment_ids:
                continue
            employee = tds.hr_employee_id or tds.hr_contract_id.employee_id
            if not employee or not tds.tds_from_date or not tds.tds_to_date:
                continue

            fy_start = tds.tds_from_date
            fy_end = tds.tds_to_date

            contracts = self.env['hr.contract'].search([
                ('employee_id', '=', employee.id),
                ('state', 'in', ['open', 'close']),
                ('date_start', '<=', fy_end),
                '|',
                ('date_end', '=', False),
                ('date_end', '>=', fy_start),
            ], order='date_start')

            if not contracts:
                continue

            line_vals_list = []
            for idx, contract in enumerate(contracts):
                monthly_gross = contract.gross if contract.gross else contract.wage
                if not monthly_gross:
                    continue

                effective_from = max(contract.date_start or fy_start, fy_start)
                effective_to = min(contract.date_end or fy_end, fy_end)
                if effective_from and effective_to and effective_from <= effective_to:
                    line_vals_list.append({
                        'hr_tds_id': tds.id,
                        'line_type': 'monthly',
                        'effective_from': effective_from,
                        'effective_to': effective_to,
                        'monthly_gross': monthly_gross,
                        'increment_reason': 'joining' if idx == 0 else 'increment',
                        'remarks': f'Auto from contract {contract.name}',
                    })

            if line_vals_list:
                SalaryIncrement.create(line_vals_list)

    @api.depends('tax_regime_slab', 'tax_regime_slab.allowed_scheme_ids')
    def _compute_has_slab_scheme_config(self):
        for rec in self:
            rec.has_slab_scheme_config = bool(rec.tax_regime_slab and rec.tax_regime_slab.allowed_scheme_ids)

    @api.depends('tax_regime_slab', 'tax_regime_type', 'tax_regime_slab.allowed_scheme_ids')
    def _compute_available_scheme_ids(self):
        Scheme = self.env['tds.section.scheme']
        for rec in self:
            if rec.tax_regime_slab and rec.tax_regime_slab.allowed_scheme_ids:
                rec.available_scheme_ids = rec.tax_regime_slab.allowed_scheme_ids
            elif rec.tax_regime_type:
                rec.available_scheme_ids = Scheme.search([
                    ('applicable_regime', 'in', ['both', rec.tax_regime_type]),
                ])
            else:
                rec.available_scheme_ids = Scheme.search([])

    @api.depends('available_scheme_ids', 'available_scheme_ids.section_id')
    def _compute_available_section_ids(self):
        for rec in self:
            rec.available_section_ids = rec.available_scheme_ids.mapped('section_id')
    
    @api.depends('deduction_ids', 'deduction_ids.deduction_amt', 'deduction_ids.tax_regime_type')
    def _compute_regime_deduction_totals(self):
        """Calculate total deductions for each regime"""
        for rec in self:
            old_regime_deds = rec.deduction_ids.filtered(lambda d: d.tax_regime_type == 'old')
            new_regime_deds = rec.deduction_ids.filtered(lambda d: d.tax_regime_type == 'new')
            
            rec.old_regime_total_deductions = sum(old_regime_deds.mapped('deduction_amt'))
            rec.new_regime_total_deductions = sum(new_regime_deds.mapped('deduction_amt'))

    @api.onchange('use_salary_increments')
    def _onchange_use_salary_increments(self):
        """Auto-populate initial salary increment line from contract when enabled"""
        if self.use_salary_increments and not self.salary_increment_ids and self.hr_contract_id:
            contract = self.hr_contract_id
            from_date = contract.date_start if contract.date_start else self.tds_from_date
            if self.tds_from_date and from_date and from_date < self.tds_from_date:
                from_date = self.tds_from_date
            to_date = self.tds_to_date
            monthly_gross = contract.gross if contract.gross else contract.wage
            
            if from_date and to_date and monthly_gross:
                self.salary_increment_ids = [(0, 0, {
                    'effective_from': from_date,
                    'effective_to': to_date,
                    'monthly_gross': monthly_gross,
                    'increment_reason': 'joining',
                    'remarks': f'Initial salary from contract {contract.name}'
                })]

    @api.onchange('tax_regime_slab')
    def _onchange_tax_regime_slab(self):
        """Auto-populate available deduction lines when the Tax Slab (regime) changes.

        Behavior:
        - Always sync `tax_regime_type` from the selected slab.
        - Ensure deduction lines exist for all schemes available in that regime.
        - Preserve any existing user-entered amounts.
        - Keep deduction lines of the other regime intact.
        """
        if not self.tax_regime_slab:
            return

        regime_type = self.tax_regime_slab.tax_regime_type
        if not regime_type:
            return

        self.tax_regime_type = regime_type

        Scheme = self.env['tds.section.scheme']
        if self.tax_regime_slab.allowed_scheme_ids:
            available_schemes = self.tax_regime_slab.allowed_scheme_ids
        else:
            available_schemes = Scheme.search([
                ('applicable_regime', 'in', ['both', regime_type]),
            ])

        # Keep existing lines for both regimes.
        existing_lines = self.deduction_ids
        existing_other_regime = existing_lines.filtered(lambda l: l.tax_regime_type and l.tax_regime_type != regime_type)
        existing_this_regime = existing_lines.filtered(lambda l: (l.tax_regime_type or regime_type) == regime_type)

        # Map existing by scheme (preferred) to preserve user amounts.
        existing_by_scheme_id = {l.scheme_id.id: l for l in existing_this_regime if l.scheme_id}

        cmds = [(5, 0, 0)]

        # Re-add the other regime lines (keep as-is).
        for line in existing_other_regime:
            cmds.append((4, line.id))

        # Ensure we have one line per available scheme for the selected regime.
        for scheme in available_schemes:
            if not scheme or not scheme.id:
                continue
            existing = existing_by_scheme_id.get(scheme.id)
            if existing:
                # Keep the existing line (user amount preserved).
                cmds.append((4, existing.id))
                continue

            # Create a new line. Default amount to max limit (keeps previous behavior).
            # Users can edit the amount as needed.
            cmds.append((0, 0, {
                'section_id': scheme.section_id.id if scheme.section_id else False,
                'scheme_id': scheme.id,
                'deduction_amt': scheme.max_limit_deduction or 0.0,
                'tax_regime_type': regime_type,
                'name': '%s - %s' % (
                    (scheme.section_id.name or ''),
                    (scheme.display_name or scheme.scheme_name or ''),
                ),
            }))

        self.deduction_ids = cmds

    @api.onchange('is_tds_payslip')
    def _onchange_is_tds_payslip(self):
        for record in self:
            if not record.is_tds_payslip or not record.hr_employee_id:
                continue
            from_date = record.tds_from_date
            to_date = record.tds_to_date
            if not from_date or not to_date:
                continue

            existing_record = self.search([
                ('hr_employee_id', '=', record.hr_employee_id.id),
                ('is_tds_payslip', '=', True),
                ('id', '!=', record.id or 0),
                ('tds_from_date', '<=', to_date),
                ('tds_to_date', '>=', from_date),
            ], limit=1)
            if existing_record:
                raise ValidationError("Only one TDS record can be active on payslip for the same period.")

                # payslips = self.env['hr.payslip'].sudo().search([
                #     ('employee_id', '=', record.hr_employee_id.id),
                #     ('state', 'in', ['done', 'paid']),
                #     ('date_from', '>=', record.tds_from_date), ('date_from', '<=', record.tds_to_date)
                # ])
                # if payslips and record._origin.is_tds_payslip:
                #     raise ValidationError(
                #         "Payslips have already been generated from the period of start and end date of TDS"
                #     )

    @api.constrains('previous_employer_from_date', 'previous_employer_to_date', 'tds_from_date', 'tds_to_date')
    def _check_previous_employer_period(self):
        for record in self:
            if record.previous_employer_from_date and record.previous_employer_to_date and record.previous_employer_to_date < record.previous_employer_from_date:
                raise ValidationError('Previous Employer To Date must be greater than or equal to From Date.')
            if record.previous_employer_from_date and record.tds_from_date and record.previous_employer_from_date < record.tds_from_date:
                raise ValidationError('Previous Employer From Date must be within the TDS financial year.')
            if record.previous_employer_to_date and record.tds_to_date and record.previous_employer_to_date > record.tds_to_date:
                raise ValidationError('Previous Employer To Date must be within the TDS financial year.')

    def _get_previous_employer_period_clipped(self, fy_start, fy_end):
        self.ensure_one()
        prev_from = self.previous_employer_from_date
        prev_to = self.previous_employer_to_date
        if not prev_from or not prev_to:
            return False, False
        prev_from = max(prev_from, fy_start) if fy_start else prev_from
        prev_to = min(prev_to, fy_end) if fy_end else prev_to
        if prev_to < prev_from:
            return False, False
        return prev_from, prev_to

    def _is_previous_employer_month(self, month_start, prev_from, prev_to):
        self.ensure_one()
        if not prev_from or not prev_to:
            return False
        month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
        return month_start <= prev_to and month_end >= prev_from

    def _is_current_employer_month_by_contract(self, month_start, contract_start):
        """Return True if the given calendar month overlaps current employer contract start.

        When there is no explicit previous employer period, we consider a month to belong to
        the current employer if any day of that month is on/after the contract start date.
        That is, month_end >= contract_start.
        """
        if not contract_start or not month_start:
            return True
        month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
        return month_end >= contract_start

    def _count_previous_employer_months(self, fy_start, fy_end, contract_start):
        self.ensure_one()
        prev_from, prev_to = self._get_previous_employer_period_clipped(fy_start, fy_end)
        if prev_from and prev_to:
            count = 0
            current_date = fy_start
            while current_date <= fy_end:
                if self._is_previous_employer_month(current_date, prev_from, prev_to):
                    count += 1
                current_date += relativedelta(months=1)
            return count
        prev_months = 0
        if contract_start and fy_start and contract_start > fy_start:
            delta_prev = relativedelta(contract_start, fy_start)
            prev_months = (delta_prev.years * 12) + delta_prev.months
        return prev_months

    @api.constrains('hr_employee_id', 'is_tds_payslip', 'tds_from_date', 'tds_to_date')
    def _check_unique_active_tds_per_period(self):
        for record in self:
            if not record.is_tds_payslip or not record.hr_employee_id:
                continue
            if not record.tds_from_date or not record.tds_to_date:
                continue
            existing_record = self.search([
                ('hr_employee_id', '=', record.hr_employee_id.id),
                ('is_tds_payslip', '=', True),
                ('id', '!=', record.id),
                ('tds_from_date', '<=', record.tds_to_date),
                ('tds_to_date', '>=', record.tds_from_date),
            ], limit=1)
            if existing_record:
                raise ValidationError("Only one TDS record can be active on payslip for the same period.")




    @api.depends('annual_salary', 'previous_employer_taxable', 'perquisites_17_2', 'profits_17_3')
    def _compute_income_chargeable_salaries(self):
        for tds in self:
            # Interim: No deductions/exemptions considered; compute pure gross income for FY.
            # Income chargeable = Gross Salary + Perquisites + Profits + Previous Employer Income
            gross_income = (tds.annual_salary or 0.0) + (tds.previous_employer_taxable or 0.0) + (tds.perquisites_17_2 or 0.0) + (tds.profits_17_3 or 0.0)
            tds.income_chargeable_salaries = float(gross_income)

    @api.depends('travel_concession_10_5', 'gratuity_10_10', 'commuted_pension_10_10a', 'leave_salary_10_10aa', 'other_exemptions_10', 'tax_regime_type')
    def _compute_total_exemptions_10(self):
        for tds in self:
            if tds.tax_regime_type == 'new':
                tds.total_exemptions_10 = 0.0
            else:
                tds.total_exemptions_10 = (
                    (tds.travel_concession_10_5 or 0.0) +
                    (tds.gratuity_10_10 or 0.0) +
                    (tds.commuted_pension_10_10a or 0.0) +
                    (tds.leave_salary_10_10aa or 0.0) +
                    (tds.other_exemptions_10 or 0.0)
                )

    @api.depends('rent_payment_ids', 'rent_payment_ids.total_rent_paid')
    def _compute_total_rent_paid(self):
        for tds in self:
            tds.total_rent_paid = sum(tds.rent_payment_ids.mapped('total_rent_paid'))
            # Mirror into legacy field so user sees rent in single-period section too
            tds.actual_rental_paid = tds.total_rent_paid

    @api.depends(
        'rent_payment_ids',
        'rent_payment_ids.total_rent_paid',
        'use_multiple_rent_periods',
        'basic_salary',
        'hra_received',
        'rent_excess_per',
        'hra_per',
        'final_hra_amt',
        'tax_regime_type',
    )
    def _compute_total_hra_exemption(self):
        for tds in self:
            if tds.tax_regime_type == 'new':
                tds.total_hra_exemption = 0.0
                continue
            # When using multiple rent periods, compute exemption from summed rent.
            # For legacy/single-period mode, use the final_hra_amt computed from manual inputs.
            if tds.use_multiple_rent_periods and tds.rent_payment_ids:
                total_rent = sum(tds.rent_payment_ids.mapped('total_rent_paid'))
                salary_for_hra = tds.basic_salary or 0.0
                hra_received = tds.hra_received or 0.0
                excess_percent = tds.rent_excess_per or 10.0

                # Use the HRA % configured on the TDS record (user can keep 40/50/etc.).
                # If not set, default to 40%.
                hra_percent = tds.hra_per or 40.0

                rent_paid_excess = total_rent - (salary_for_hra * excess_percent / 100.0)
                rent_paid_excess = max(rent_paid_excess, 0.0)
                salary_percent_amount = salary_for_hra * (hra_percent / 100.0)

                tds.total_hra_exemption = max(min(hra_received, rent_paid_excess, salary_percent_amount), 0.0)
            else:
                tds.total_hra_exemption = tds.final_hra_amt

    @api.depends('basic_salary', 'actual_rental_paid', 'rent_excess_per')
    def _compute_rent_exempt(self):
        for tds in self:
            # Rent paid in excess of 10% (or configured %) of salary.
            excess_percent = tds.rent_excess_per or 10.0
            rent_paid_excess = (tds.actual_rental_paid or 0.0) - ((tds.basic_salary or 0.0) * excess_percent / 100.0)
            tds.rent_exempt_amt = max(rent_paid_excess, 0.0)

    @api.depends('hra_per')
    def _compute_hra_amt(self):
        for tds in self:
            # Salary % component (40% non-metro / 50% metro).
            tds.hra_amt = ((tds.basic_salary or 0.0) * (tds.hra_per or 0.0)) / 100.0

    @api.depends('rent_exempt_amt', 'hra_amt', 'hra_received')
    def _compute_final_hra(self):
        for tds in self:
            # Standard HRA exemption = min(
            # 1) HRA received
            # 2) Rent paid - 10% of salary
            # 3) 40%/50% of salary
            # Never negative.
            hra_received = tds.hra_received or 0.0
            rent_paid_excess = tds.rent_exempt_amt or 0.0
            salary_percent_amount = tds.hra_amt or 0.0
            tds.final_hra_amt = max(min(hra_received, rent_paid_excess, salary_percent_amount), 0.0)

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.hr_employee_id.name or ''} - {rec.tax_regime_slab.display_name or ''}"

    # Removed overly restrictive validation - employees can have multiple TDS records
    # with the same tax regime for different periods. The real constraint is on
    # is_tds_payslip (enforced in _onchange_is_tds_payslip method)


    def sort_financial_year(self, month_years):
        # Define the correct order for financial year sorting (April to March)
        financial_order = {
            "April": 1, "May": 2, "June": 3, "July": 4, "August": 5, "September": 6,
            "October": 7, "November": 8, "December": 9, "January": 10, "February": 11, "March": 12
        }

        # Custom sorting key
        def financial_key(month_year):
            month, year = month_year.split(" ")
            return (int(year), financial_order[month])

        return sorted(month_years, key=financial_key)

    @api.depends('month_ids')
    def _compute_month_ids(self):
        for record in self:
            if record.month_ids:
                # record.write({'tds_deduction_month': round(record.tax_payable / len(record.month_ids)), 'tds_deduction_month_cess': round(record.tax_payable_cess / len(record.month_ids))})
                month_years = sorted(record.month_ids.mapped("tds_month_year"))
                sorted_month_years = self.sort_financial_year(month_years)
                record.tds_from_month = sorted_month_years[0] if sorted_month_years else False
                record.tds_to_month = sorted_month_years[-1] if sorted_month_years else False

    @api.depends(
        'month_ids',
        'month_ids.tds_month_year',
        'month_ids.tds_month_amt',
        'month_ids.is_previous_employer',
        'tax_round_off_amount',
        'prepaid_tds',
        'tax_payable_cess',
        'tds_from_date',
        'tds_to_date',
        'hr_contract_id',
        'hr_contract_id.date_start',
        'previous_employer_from_date',
        'previous_employer_to_date',
        'salary_increment_ids',
        'salary_increment_ids.line_type',
        'salary_increment_ids.effective_from',
        'salary_increment_ids.effective_to',
        'salary_increment_ids.monthly_gross',
        'salary_increment_ids.one_time_amount',
        'salary_increment_ids.one_time_tds'
    )
    def _compute_monthly_breakdown_html(self):
        for record in self:
            month_lines = []
            fy_start = record.tds_from_date
            fy_end = record.tds_to_date
            if not fy_start or not fy_end:
                record.monthly_breakdown_html = ""
                continue

            contract_start = record._get_current_employer_start_date(fy_start, fy_end)

            employee = record.hr_employee_id or (record.hr_contract_id.employee_id if record.hr_contract_id else False)
            fy_contracts = self.env['hr.contract']
            if employee:
                fy_contracts = self.env['hr.contract'].search([
                    ('employee_id', '=', employee.id),
                    ('state', 'in', ['open', 'close']),
                    ('date_start', '<=', fy_end),
                    '|',
                    ('date_end', '=', False),
                    ('date_end', '>=', fy_start),
                ], order='date_start')

            salary_increments = record.salary_increment_ids

            def _month_bounds(d):
                ms = d.replace(day=1)
                me = ms + relativedelta(months=1, days=-1)
                return ms, me

            def _overlap_days(a_from, a_to, b_from, b_to):
                start = max(a_from, b_from)
                end = min(a_to, b_to)
                if not start or not end or start > end:
                    return 0
                return (end - start).days + 1

            def _monthly_gross_for_date(d):
                # Prorate monthly gross by effective days of salary increment lines within the month
                ms, me = _month_bounds(d)
                total_days = (me - ms).days + 1
                gross_total = 0.0
                if salary_increments:
                    monthly_lines = salary_increments.filtered(
                        lambda l: l.line_type == 'monthly'
                        and (l.effective_from or fy_start) <= me
                        and ((l.effective_to or fy_end) >= ms)
                    )
                    for l in monthly_lines:
                        l_from = l.effective_from or ms
                        l_to = l.effective_to or me
                        od = _overlap_days(ms, me, l_from, l_to)
                        if od > 0 and total_days > 0:
                            gross_total += float(l.monthly_gross or 0.0) * (float(od) / float(total_days))

                    one_time_lines = salary_increments.filtered(
                        lambda l: l.line_type == 'one_time'
                        and l.effective_from
                        and l.effective_from.year == d.year
                        and l.effective_from.month == d.month
                    )
                    one_time_amt = float(sum(one_time_lines.mapped('one_time_amount')) or 0.0)
                    return float(gross_total) + float(one_time_amt)

                # Fallback from contracts (not using increments): not prorated due to unknown policy
                if fy_contracts:
                    ms, me = _month_bounds(d)
                    matched = fy_contracts.filtered(lambda c: (c.date_start or fy_start) <= me and ((c.date_end or fy_end) >= ms))
                    if matched:
                        chosen = matched.sorted(lambda c: c.date_start or fy_start)[-1]
                        monthly_salary = chosen.gross if getattr(chosen, 'gross', 0.0) else (chosen.wage or 0.0)
                        return float(monthly_salary or 0.0)
                # Fallback
                if record.current_ctc:
                    return float(record.current_ctc or 0.0) / 12.0
                if record.hr_contract_id and getattr(record.hr_contract_id, 'wage', False):
                    return float(record.hr_contract_id.wage or 0.0)
                return 0.0

            def _one_time_addons_for_date(d):
                if not salary_increments:
                    return 0.0
                one_time_lines = salary_increments.filtered(
                    lambda l: l.line_type == 'one_time'
                    and l.effective_from
                    and l.effective_from.year == d.year
                    and l.effective_from.month == d.month
                )
                return float(sum(one_time_lines.mapped('one_time_amount')) or 0.0)

            # Prepaid split over previous employer months
            prev_months = record._count_previous_employer_months(fy_start, fy_end, contract_start)
            monthly_prev = float(math.ceil((record.prepaid_tds or 0.0) / prev_months)) if prev_months else 0.0

            # Compute base and rounded totals (current employer share only)
            base_total = max((record.tax_payable_cess or 0.0) - (record.prepaid_tds or 0.0), 0.0)
            rounded_total = max(base_total + (record.tax_round_off_amount or 0.0), 0.0)

            # Paid TDS periods (current employer): allocate per-month amounts for selected months.
            paid_by_month = {}

            # Extra one-time TDS (per one-time increment line) should be ADDED on top of base monthly allocation.
            # But the annual pool stays the same, so we subtract these fixed extras from the remaining pool.
            extra_tds_by_month = {}
            if salary_increments:
                one_time_tds_lines = salary_increments.filtered(
                    lambda l: l.line_type == 'one_time'
                    and l.effective_from
                    and (l.one_time_tds or 0.0)
                    and (l.one_time_tds or 0.0) != 0.0
                )
                for l in one_time_tds_lines:
                    key = (l.effective_from.year, l.effective_from.month)
                    extra_tds_by_month[key] = extra_tds_by_month.get(key, 0.0) + float(l.one_time_tds or 0.0)

            # Month-wise manual paid values take priority.
            if record.paid_tds_month_ids:
                for mline in record.paid_tds_month_ids:
                    if not mline.month_date:
                        continue
                    key = (mline.month_date.year, mline.month_date.month)
                    paid_by_month[key] = paid_by_month.get(key, 0.0) + float(mline.amount or 0.0)

            if (record.use_paid_tds_periods or record.paid_tds_period_ids) and record.paid_tds_period_ids:
                for p in record.paid_tds_period_ids:
                    if not p.period_from or not p.period_to or (p.period_from > p.period_to):
                        continue
                    # Clip to FY
                    p_from = max(p.period_from, fy_start)
                    p_to = min(p.period_to, fy_end)
                    if p_from > p_to:
                        continue
                    # Count months in period
                    months = []
                    cur = p_from.replace(day=1)
                    end = p_to.replace(day=1)
                    while cur <= end:
                        months.append(cur)
                        cur += relativedelta(months=1)
                    if not months:
                        continue
                    per_month = float(p.amount or 0.0) / float(len(months))
                    for m in months:
                        key = (m.year, m.month)
                        # If month-wise manual value exists, don't overwrite it.
                        if key in paid_by_month:
                            continue
                        paid_by_month[key] = paid_by_month.get(key, 0.0) + per_month

            # Duplicate block kept for safety (disabled):
            # Extra one-time TDS (per one-time increment line)
            # extra_tds_by_month = {}
            # if record.salary_increment_ids:
            #     one_time_tds_lines = record.salary_increment_ids.filtered(
            #         lambda l: l.line_type == 'one_time'
            #         and l.effective_from
            #         and (l.one_time_tds or 0.0)
            #         and (l.one_time_tds or 0.0) != 0.0
            #     )
            #     for l in one_time_tds_lines:
            #         key = (l.effective_from.year, l.effective_from.month)
            #         extra_tds_by_month[key] = extra_tds_by_month.get(key, 0.0) + float(l.one_time_tds or 0.0)

            # Extra one-time TDS (per one-time increment line)
            extra_tds_by_month = {}
            if record.salary_increment_ids:
                one_time_tds_lines = record.salary_increment_ids.filtered(
                    lambda l: l.line_type == 'one_time'
                    and l.effective_from
                    and (l.one_time_tds or 0.0)
                    and (l.one_time_tds or 0.0) != 0.0
                )
                for l in one_time_tds_lines:
                    key = (l.effective_from.year, l.effective_from.month)
                    extra_tds_by_month[key] = extra_tds_by_month.get(key, 0.0) + float(l.one_time_tds or 0.0)

            # Extra one-time TDS (per one-time increment line)
            extra_tds_by_month = {}
            if record.salary_increment_ids:
                one_time_tds_lines = record.salary_increment_ids.filtered(
                    lambda l: l.line_type == 'one_time'
                    and l.effective_from
                    and (l.one_time_tds or 0.0)
                    and (l.one_time_tds or 0.0) != 0.0
                )
                for l in one_time_tds_lines:
                    key = (l.effective_from.year, l.effective_from.month)
                    extra_tds_by_month[key] = extra_tds_by_month.get(key, 0.0) + float(l.one_time_tds or 0.0)

            # Extra one-time TDS (per one-time increment line)
            extra_tds_by_month = {}
            if record.salary_increment_ids:
                one_time_tds_lines = record.salary_increment_ids.filtered(
                    lambda l: l.line_type == 'one_time'
                    and l.effective_from
                    and (l.one_time_tds or 0.0)
                    and (l.one_time_tds or 0.0) != 0.0
                )
                for l in one_time_tds_lines:
                    key = (l.effective_from.year, l.effective_from.month)
                    extra_tds_by_month[key] = extra_tds_by_month.get(key, 0.0) + float(l.one_time_tds or 0.0)

            # Count current-employer months
            total_months = 0
            paid_months = 0
            current_date = fy_start
            prev_from, prev_to = record._get_previous_employer_period_clipped(fy_start, fy_end)
            while current_date <= fy_end:
                is_prev = record._is_previous_employer_month(current_date, prev_from, prev_to) if (prev_from and prev_to) else (not record._is_current_employer_month_by_contract(current_date, contract_start))
                if not is_prev:
                    total_months += 1
                    if (current_date.year, current_date.month) in paid_by_month:
                        paid_months += 1
                current_date += relativedelta(months=1)

            # Attendance-weighted proportional split for current months (align with month_ids logic)
            # Build weights and amounts for remaining (unpaid) current months only
            def _count_weekdays(d_from: date, d_to: date) -> int:
                if not d_from or not d_to or d_from > d_to:
                    return 0
                c = 0
                cur = d_from
                while cur <= d_to:
                    if cur.weekday() < 5:
                        c += 1
                    cur += timedelta(days=1)
                return c

            def _attendance_present_weekdays(emp, d_from: date, d_to: date) -> int:
                if not emp or not d_from or not d_to or d_from > d_to:
                    return 0
                Att = record.env['hr.attendance']
                atts = Att.sudo().search([
                    ('employee_id', '=', (record.hr_employee_id or record.hr_contract_id.employee_id).id if (record.hr_employee_id or (record.hr_contract_id and record.hr_contract_id.employee_id)) else 0),
                    ('check_in', '>=', datetime.combine(d_from, datetime.min.time())),
                    ('check_in', '<=', datetime.combine(d_to, datetime.max.time())),
                ])
                dates = set()
                for a in atts:
                    d = (a.check_in.date() if a.check_in else None)
                    if d and (d >= d_from and d <= d_to) and d.weekday() < 5:
                        dates.add(d)
                return len(dates)

            remaining_base = 0.0
            paid_total = sum(paid_by_month.values()) if paid_by_month else 0.0
            extra_total = sum(extra_tds_by_month.values()) if extra_tds_by_month else 0.0
            remaining_base = max(float(base_total) - float(paid_total) - float(extra_total), 0.0)
            remaining_rounded = max(float(rounded_total) - float(paid_total) - float(extra_total), 0.0)

            weights = {}
            order_months = []
            sum_w = 0.0
            employee = record.hr_employee_id or (record.hr_contract_id.employee_id if record.hr_contract_id else False)

            probe_date = fy_start
            prev_from, prev_to = record._get_previous_employer_period_clipped(fy_start, fy_end)
            while probe_date <= fy_end:
                # Consider month as current if any salary increment overlaps it
                ms_tmp, me_tmp = _month_bounds(probe_date)
                inc_overlap = False
                if record.salary_increment_ids:
                    inc_overlap = bool(record.salary_increment_ids.filtered(
                        lambda l: l.line_type == 'monthly' and (l.effective_from or ms_tmp) <= me_tmp and (l.effective_to or me_tmp) >= ms_tmp
                    ))
                is_prev = False
                if prev_from and prev_to and record._is_previous_employer_month(probe_date, prev_from, prev_to):
                    is_prev = True
                elif not inc_overlap and not record._is_current_employer_month_by_contract(probe_date, contract_start):
                    is_prev = True
                key = (probe_date.year, probe_date.month)
                if not is_prev and key not in paid_by_month:
                    ms, me = _month_bounds(probe_date)
                    full_start = max(ms, fy_start)
                    full_end = min(me, fy_end)
                    # Determine effective employment window for this month:
                    # Prefer salary increment lines if available and overlapping this month; otherwise fallback to contract.
                    eff_start = full_start
                    eff_end = full_end
                    if record.salary_increment_ids:
                        inc_lines = record.salary_increment_ids.filtered(lambda l: l.line_type == 'monthly' and (l.effective_from or full_start) <= full_end and (l.effective_to or full_end) >= full_start)
                        if inc_lines:
                            min_from = min([l.effective_from or full_start for l in inc_lines])
                            max_to = max([l.effective_to or full_end for l in inc_lines])
                            eff_start = max(full_start, min_from)
                            eff_end = min(full_end, max_to)
                        else:
                            eff_start = max(full_start, contract_start or full_start)
                            eff_end = full_end
                            if record.hr_contract_id and record.hr_contract_id.date_end:
                                eff_end = min(eff_end, record.hr_contract_id.date_end)
                    else:
                        eff_start = max(full_start, contract_start or full_start)
                        eff_end = full_end
                        if record.hr_contract_id and record.hr_contract_id.date_end:
                            eff_end = min(eff_end, record.hr_contract_id.date_end)
                    # Use calendar days within the month (not weekdays/attendance)
                    full_days = (full_end - full_start).days + 1 if (full_end and full_start and full_end >= full_start) else 0
                    eff_days = (eff_end - eff_start).days + 1 if (eff_end and eff_start and eff_end >= eff_start) else 0
                    w = float(eff_days) / float(full_days) if full_days else 0.0
                    weights[key] = w
                    order_months.append(key)
                    sum_w += w
                probe_date += relativedelta(months=1)

            proportional_amounts = {}
            proportional_amounts_rounded = {}
            allocated_sum = 0.0
            allocated_sum_rounded = 0.0
            if sum_w > 0:
                # Actual allocation (without round off)
                if remaining_base > 0:
                    for i, key in enumerate(order_months):
                        if i < len(order_months) - 1:
                            amt = remaining_base * (weights.get(key, 0.0) / sum_w)
                            amt = float(math.ceil(amt)) if amt > 0 else 0.0
                            proportional_amounts[key] = amt
                            allocated_sum += amt
                        else:
                            proportional_amounts[key] = float(max(remaining_base - allocated_sum, 0.0))

                # Rounded allocation (with round off)
                if remaining_rounded > 0:
                    for i, key in enumerate(order_months):
                        if i < len(order_months) - 1:
                            amt = remaining_rounded * (weights.get(key, 0.0) / sum_w)
                            amt = float(math.ceil(amt)) if amt > 0 else 0.0
                            proportional_amounts_rounded[key] = amt
                            allocated_sum_rounded += amt
                        else:
                            proportional_amounts_rounded[key] = float(max(remaining_rounded - allocated_sum_rounded, 0.0))
            else:
                # Fallback equal split to remaining months
                remaining_months = max(total_months - paid_months, 0)
                monthly_cur_actual = float(remaining_base) / float(remaining_months) if remaining_months else 0.0
                monthly_cur_rounded = float(remaining_rounded) / float(remaining_months) if remaining_months else 0.0
                for key in order_months:
                    proportional_amounts[key] = float(math.ceil(monthly_cur_actual)) if monthly_cur_actual > 0 else 0.0
                    proportional_amounts_rounded[key] = float(math.ceil(monthly_cur_rounded)) if monthly_cur_rounded > 0 else 0.0

            # Build rows for entire FY, marking previous/current employer
            current_date = fy_start
            prev_from, prev_to = record._get_previous_employer_period_clipped(fy_start, fy_end)
            while current_date <= fy_end:
                month_name = current_date.strftime("%B")
                year = current_date.year
                # Consider month as current if any salary increment overlaps it
                ms_tmp, me_tmp = _month_bounds(current_date)
                inc_overlap = False
                if record.salary_increment_ids:
                    inc_overlap = bool(record.salary_increment_ids.filtered(
                        lambda l: l.line_type == 'monthly' and (l.effective_from or ms_tmp) <= me_tmp and (l.effective_to or me_tmp) >= ms_tmp
                    ))
                is_previous = False
                if prev_from and prev_to and record._is_previous_employer_month(current_date, prev_from, prev_to):
                    is_previous = True
                elif not inc_overlap and not record._is_current_employer_month_by_contract(current_date, contract_start):
                    is_previous = True
                if is_previous:
                    tds_amount_actual = monthly_prev
                    tds_amount_rounded = monthly_prev
                else:
                    key = (current_date.year, current_date.month)
                    paid_val = paid_by_month.get(key)
                    extra_val = extra_tds_by_month.get(key, 0.0)
                    if (record.use_paid_tds_periods or record.paid_tds_period_ids) and paid_val is not None:
                        tds_amount_actual = float(paid_val or 0.0) + float(extra_val or 0.0)
                        tds_amount_rounded = float(paid_val or 0.0) + float(extra_val or 0.0)
                    else:
                        # Base allocation + extra one-time TDS (if any)
                        base_alloc_actual = proportional_amounts.get(key, 0.0)
                        base_alloc_rounded = proportional_amounts_rounded.get(key, base_alloc_actual)
                        tds_amount_actual = float(base_alloc_actual or 0.0) + float(extra_val or 0.0)
                        tds_amount_rounded = float(base_alloc_rounded or 0.0) + float(extra_val or 0.0)

                month_lines.append({
                    'month_date': current_date,
                    'tds_month_year': f"{month_name} {year}",
                    'is_previous_employer': is_previous,
                    'tds_month_amt': tds_amount_actual,
                    'tds_month_amt_rounded': tds_amount_rounded,
                })
                current_date += relativedelta(months=1)

            rows = []
            has_previous_employer_rows = False
            total_rows_count = 0
            total_gross = 0.0
            total_tds_actual = 0.0
            total_tds_rounded = 0.0

            for line in month_lines:
                if isinstance(line, dict):
                    month = line.get('tds_month_year') or ''
                    month_date = line.get('month_date')
                    is_prev = bool(line.get('is_previous_employer'))
                    amt_actual = line.get('tds_month_amt') or 0.0
                    amt_rounded = line.get('tds_month_amt_rounded', line.get('tds_month_amt')) or 0.0
                else:
                    month = line.tds_month_year or ''
                    month_date = getattr(line, 'month_date', False)
                    is_prev = bool(getattr(line, 'is_previous_employer', False))
                    amt_actual = line.tds_month_amt or 0.0
                    # fallback rounded equals actual for persisted lines
                    amt_rounded = getattr(line, 'tds_month_amt_rounded', amt_actual) if hasattr(line, 'tds_month_amt_rounded') else amt_actual

                # User requirement: do not show previous-employer month-wise breakup in the table.
                if is_prev:
                    has_previous_employer_rows = True
                    continue

                # Display: always round up to next rupee
                try:
                    amt_actual = float(math.ceil(float(amt_actual)))
                    amt_rounded = float(math.ceil(float(amt_rounded)))
                except Exception:
                    amt_actual = float(amt_actual or 0.0)
                    amt_rounded = float(amt_rounded or 0.0)

                prev = 'Previous' if is_prev else 'Current'
                row_class = 'kpt-prev' if is_prev else 'kpt-cur'

                gross_monthly = 0.0
                addons_amt = 0.0
                try:
                    if month_date:
                        gross_monthly = _monthly_gross_for_date(month_date)
                        addons_amt = _one_time_addons_for_date(month_date)
                    else:
                        gross_monthly = _monthly_gross_for_date(fy_start)
                        addons_amt = _one_time_addons_for_date(fy_start)
                except Exception:
                    gross_monthly = 0.0
                    addons_amt = 0.0

                try:
                    gross_monthly_display = float(math.ceil(float(gross_monthly or 0.0)))
                except Exception:
                    gross_monthly_display = float(gross_monthly or 0.0)

                try:
                    addons_amt_display = float(math.ceil(float(addons_amt or 0.0)))
                except Exception:
                    addons_amt_display = float(addons_amt or 0.0)

                base_salary_display = max(float(gross_monthly_display or 0.0) - float(addons_amt_display or 0.0), 0.0)
                if addons_amt_display:
                    gross_cell = f"{base_salary_display:,.0f} + {addons_amt_display:,.0f}"
                else:
                    gross_cell = f"{gross_monthly_display:,.0f}"

                total_rows_count += 1
                total_gross += float(gross_monthly_display or 0.0)
                total_tds_actual += float(amt_actual or 0.0)
                total_tds_rounded += float(amt_rounded or 0.0)

                rows.append(
                    f"<tr class='{row_class}'>"
                    f"<td>{month}</td>"
                    f"<td>{prev}</td>"
                    f"<td style='text-align:right;'>{gross_cell}</td>"
                    f"<td style='text-align:right;'>{amt_actual:,.0f}</td>"
                    f"<td style='text-align:right;'>{amt_rounded:,.0f}</td>"
                    f"</tr>"
                )

            if total_rows_count:
                rows.append(
                    "<tr class='kpt-total'>"
                    "<td colspan='2' style='font-weight:bold;text-align:right;'>Total</td>"
                    f"<td style='text-align:right;font-weight:bold;'>{total_gross:,.0f}</td>"
                    f"<td style='text-align:right;font-weight:bold;'>{total_tds_actual:,.0f}</td>"
                    f"<td style='text-align:right;font-weight:bold;'>{total_tds_rounded:,.0f}</td>"
                    "</tr>"
                )

            if not rows:
                rows.append(
                    "<tr class='kpt-empty'>"
                    "<td colspan='5' style='text-align:center;color:#6b7280;'>No monthly breakdown available</td>"
                    "</tr>"
                )

            prev_from, prev_to = record._get_previous_employer_period_clipped(fy_start, fy_end)
            prev_total = float(record.prepaid_tds or 0.0)
            prev_summary = ""
            prev_from_str = prev_from.strftime('%d-%m-%Y') if prev_from else ''
            prev_to_str = prev_to.strftime('%d-%m-%Y') if prev_to else ''
            if prev_total and (prev_from and prev_to):
                prev_summary = (
                    "<div style='margin:6px 0 10px 0;font-size:13px;font-weight:bold;'>"
                    "<strong>Previous employer TDS deducted</strong> "
                    f"(Period: {prev_from_str} to {prev_to_str}): "
                    f"<strong>{prev_total:,.2f}</strong>"
                    "</div>"
                )
            elif prev_total and has_previous_employer_rows:
                prev_summary = (
                    "<div style='margin:6px 0 10px 0;font-size:13px;font-weight:bold;'>"
                    "<strong>Previous employer TDS deducted</strong>: "
                    f"<strong>{prev_total:,.2f}</strong>"
                    "</div>"
                )

            paid_total_current = float(paid_total or 0.0)
            excess_paid = max(paid_total_current - float(base_total or 0.0), 0.0)
            excess_summary = ""
            if excess_paid:
                excess_summary = (
                    "<div style='margin:6px 0 10px 0;font-size:13px;font-weight:bold;'>"
                    "<strong>Excess TDS paid (Refundable)</strong>: "
                    f"<strong>{excess_paid:,.2f}</strong>"
                    "</div>"
                )

            record.monthly_breakdown_html = (
                "<style>"
                ".kpt-monthly-table{width:100%;border-collapse:collapse;table-layout:auto;}"
                ".kpt-monthly-table th,.kpt-monthly-table td{border:1px solid #e5e7eb;padding:8px;vertical-align:top;}"
                ".kpt-monthly-table th{background:#f8fafc;text-align:left;white-space:nowrap;}"
                ".kpt-monthly-table td{white-space:normal;word-break:normal;overflow-wrap:break-word;}"
                ".kpt-monthly-table tr.kpt-prev{color:#6b7280;background:#fafafa;}"
                ".kpt-monthly-table tr.kpt-total td{background:#f3f4f6;}"
                "</style>"
                "<div style='width:100%;'>"
                f"{prev_summary}"
                f"{excess_summary}"
                "<table class='kpt-monthly-table'>"
                "<thead><tr><th>Month</th><th>Employer</th><th style='text-align:right;'>Monthly Gross Salary</th><th style='text-align:right;'>Monthly TDS (Actual)</th><th style='text-align:right;'>Monthly TDS (With Round Off)</th></tr></thead>"
                f"<tbody>{''.join(rows)}</tbody>"
                "</table>"
                "</div>"
            )

    def _sync_month_ids_lines(self):
        """Generate month_ids lines server-side so it persists after save/reopen (not only via onchange)."""
        if self.env.context.get('skip_month_sync'):
            return
        for record in self:
            if not record.tds_from_date or not record.tds_to_date:
                continue

            fy_start = record.tds_from_date
            fy_end = record.tds_to_date
            contract_start = record._get_current_employer_start_date(fy_start, fy_end)

            prev_months = record._count_previous_employer_months(fy_start, fy_end, contract_start)
            monthly_prev = float(math.ceil((record.prepaid_tds or 0.0) / prev_months)) if prev_months else 0.0

            # --- Align month_ids allocation to the same logic used in Monthly Breakdown (paid months + remaining distribution) ---
            def _month_bounds(d: date):
                m_start = d.replace(day=1)
                m_end = (m_start + relativedelta(months=1)) - timedelta(days=1)
                return m_start, m_end

            def _count_weekdays(d_from: date, d_to: date) -> int:
                if not d_from or not d_to or d_from > d_to:
                    return 0
                c = 0
                cur = d_from
                while cur <= d_to:
                    if cur.weekday() < 5:
                        c += 1
                    cur += timedelta(days=1)
                return c

            def _attendance_present_weekdays(emp, d_from: date, d_to: date) -> int:
                if not emp or not d_from or not d_to or d_from > d_to:
                    return 0
                Att = record.env['hr.attendance']
                atts = Att.sudo().search([
                    ('employee_id', '=', emp.id),
                    ('check_in', '>=', datetime.combine(d_from, datetime.min.time())),
                    ('check_in', '<=', datetime.combine(d_to, datetime.max.time())),
                ])
                dates = set()
                for a in atts:
                    d = (a.check_in.date() if a.check_in else None)
                    if d and (d >= d_from and d <= d_to) and d.weekday() < 5:
                        dates.add(d)
                return len(dates)

            # Compute totals (current employer share only)
            base_total = max((record.tax_payable_cess or 0.0) - (record.prepaid_tds or 0.0), 0.0)
            rounded_total = max(float(base_total) + float(record.tax_round_off_amount or 0.0), 0.0)

            # Paid TDS months (current employer)
            paid_by_month = {}
            if record.paid_tds_month_ids:
                for mline in record.paid_tds_month_ids:
                    if not mline.month_date:
                        continue
                    key = (mline.month_date.year, mline.month_date.month)
                    paid_by_month[key] = paid_by_month.get(key, 0.0) + float(mline.amount or 0.0)

            if (record.use_paid_tds_periods or record.paid_tds_period_ids) and record.paid_tds_period_ids:
                for p in record.paid_tds_period_ids:
                    if not p.period_from or not p.period_to or (p.period_from > p.period_to):
                        continue
                    p_from = max(p.period_from, fy_start)
                    p_to = min(p.period_to, fy_end)
                    if p_from > p_to:
                        continue
                    months = []
                    cur = p_from.replace(day=1)
                    end = p_to.replace(day=1)
                    while cur <= end:
                        months.append(cur)
                        cur += relativedelta(months=1)
                    if not months:
                        continue
                    per_month = float(p.amount or 0.0) / float(len(months))
                    for m in months:
                        key = (m.year, m.month)
                        if key in paid_by_month:
                            continue
                        paid_by_month[key] = paid_by_month.get(key, 0.0) + per_month

            # Extra one-time TDS (per one-time increment line)
            extra_tds_by_month = {}
            if record.salary_increment_ids:
                one_time_tds_lines = record.salary_increment_ids.filtered(
                    lambda l: l.line_type == 'one_time'
                    and l.effective_from
                    and (l.one_time_tds or 0.0)
                    and (l.one_time_tds or 0.0) != 0.0
                )
                for l in one_time_tds_lines:
                    key = (l.effective_from.year, l.effective_from.month)
                    extra_tds_by_month[key] = extra_tds_by_month.get(key, 0.0) + float(l.one_time_tds or 0.0)

            paid_total = sum(paid_by_month.values()) if paid_by_month else 0.0
            extra_total = sum(extra_tds_by_month.values()) if extra_tds_by_month else 0.0
            remaining_rounded = max(float(rounded_total) - float(paid_total) - float(extra_total), 0.0)

            # Build weights for remaining (unpaid) current months
            weights = {}
            order_months = []
            sum_w = 0.0
            employee = record.hr_employee_id or (record.hr_contract_id.employee_id if record.hr_contract_id else False)
            prev_from, prev_to = record._get_previous_employer_period_clipped(fy_start, fy_end)

            probe_date = fy_start
            total_months = 0
            paid_months = 0
            while probe_date <= fy_end:
                is_prev = record._is_previous_employer_month(probe_date, prev_from, prev_to) if (prev_from and prev_to) else (not record._is_current_employer_month_by_contract(probe_date, contract_start))
                key = (probe_date.year, probe_date.month)
                if not is_prev:
                    total_months += 1
                    if key in paid_by_month:
                        paid_months += 1
                    else:
                        ms, me = _month_bounds(probe_date)
                        full_start = max(ms, fy_start)
                        full_end = min(me, fy_end)
                        # Determine effective employment window for this month via increments first
                        eff_start = full_start
                        eff_end = full_end
                        if record.salary_increment_ids:
                            inc_lines = record.salary_increment_ids.filtered(lambda l: l.line_type == 'monthly' and (l.effective_from or full_start) <= full_end and (l.effective_to or full_end) >= full_start)
                            if inc_lines:
                                min_from = min([l.effective_from or full_start for l in inc_lines])
                                max_to = max([l.effective_to or full_end for l in inc_lines])
                                eff_start = max(full_start, min_from)
                                eff_end = min(full_end, max_to)
                            else:
                                eff_start = max(full_start, contract_start or full_start)
                                eff_end = full_end
                                if record.hr_contract_id and record.hr_contract_id.date_end:
                                    eff_end = min(eff_end, record.hr_contract_id.date_end)
                        else:
                            eff_start = max(full_start, contract_start or full_start)
                            eff_end = full_end
                            if record.hr_contract_id and record.hr_contract_id.date_end:
                                eff_end = min(eff_end, record.hr_contract_id.date_end)
                        # Use calendar days within the month (not weekdays/attendance)
                        full_days = (full_end - full_start).days + 1 if (full_end and full_start and full_end >= full_start) else 0
                        eff_days = (eff_end - eff_start).days + 1 if (eff_end and eff_start and eff_end >= eff_start) else 0
                        w = float(eff_days) / float(full_days) if full_days else 0.0
                        weights[key] = w
                        order_months.append(key)
                        sum_w += w
                probe_date += relativedelta(months=1)

            # Allocate remaining rounded across unpaid current months
            proportional_amounts_rounded = {}
            if sum_w > 0 and remaining_rounded > 0:
                allocated_sum = 0.0
                for i, key in enumerate(order_months):
                    if i < len(order_months) - 1:
                        amt = remaining_rounded * (weights.get(key, 0.0) / sum_w)
                        amt = float(math.ceil(amt)) if amt > 0 else 0.0
                        proportional_amounts_rounded[key] = amt
                        allocated_sum += amt
                    else:
                        proportional_amounts_rounded[key] = float(max(remaining_rounded - allocated_sum, 0.0))
            else:
                remaining_months = max(total_months - paid_months, 0)
                monthly_cur_rounded = float(remaining_rounded) / float(remaining_months) if remaining_months else 0.0
                allocated_sum = 0.0
                for i, key in enumerate(order_months):
                    if i < len(order_months) - 1:
                        amt = float(math.ceil(monthly_cur_rounded)) if monthly_cur_rounded > 0 else 0.0
                        proportional_amounts_rounded[key] = amt
                        allocated_sum += amt
                    else:
                        proportional_amounts_rounded[key] = float(max(remaining_rounded - allocated_sum, 0.0))

            month_cmds = [(5, 0, 0)]
            current_date = fy_start
            prev_from, prev_to = record._get_previous_employer_period_clipped(fy_start, fy_end)
            while current_date <= fy_end:
                month_name = current_date.strftime("%B")
                year = current_date.year
                is_previous = record._is_previous_employer_month(current_date, prev_from, prev_to) if (prev_from and prev_to) else (not record._is_current_employer_month_by_contract(current_date, contract_start))
                key = (current_date.year, current_date.month)
                extra_val = extra_tds_by_month.get(key, 0.0)

                if is_previous:
                    tds_amount = monthly_prev
                else:
                    paid_val = paid_by_month.get(key)
                    if (record.use_paid_tds_periods or record.paid_tds_period_ids) and paid_val is not None:
                        tds_amount = float(paid_val or 0.0) + float(extra_val or 0.0)
                    else:
                        tds_amount = float(proportional_amounts_rounded.get(key, 0.0) or 0.0) + float(extra_val or 0.0)

                month_cmds.append((0, 0, {
                    'months': month_name.lower(),
                    'tds_month_amt': tds_amount,
                    'tds_month_year': f"{month_name} {year}",
                    'is_previous_employer': is_previous,
                }))
                current_date += relativedelta(months=1)

            record.with_context(skip_month_sync=True).write({'month_ids': month_cmds})

    @api.depends(
        'tax_pay_ref',
        'hr_contract_id',
        'hr_contract_id.date_start',
        'tds_from_date',
        'tds_to_date',
        'previous_employer_from_date',
        'previous_employer_to_date',
        'prepaid_tds',
    )
    def _compute_monthly_tds(self):
        """Compute monthly TDS based on Net TDS to Pay and current-employer months only.

        The FY is split into:
        - Previous employer months (either explicit previous_employer_from/to, or fallback: months before contract start)
        - Current employer months (remaining months)

        Monthly TDS should be computed only over current employer months.
        """
        for record in self:
            if not record.tax_pay_ref:
                record.tds_deduction_month = 0.0
                record.tds_deduction_month_cess = 0.0
                continue

            fy_start = record.tds_from_date
            fy_end = record.tds_to_date if record.tds_to_date else date.fromisoformat(self.get_fy_range()[1])
            if not fy_start or not fy_end or fy_start > fy_end:
                record.tds_deduction_month = 0.0
                record.tds_deduction_month_cess = 0.0
                continue

            contract_start = record._get_current_employer_start_date(fy_start, fy_end)

            # Count only current-employer months
            current_months = 0
            current_date = fy_start
            prev_from, prev_to = record._get_previous_employer_period_clipped(fy_start, fy_end)
            while current_date <= fy_end:
                is_prev = (
                    record._is_previous_employer_month(current_date, prev_from, prev_to)
                    if (prev_from and prev_to)
                    else (not record._is_current_employer_month_by_contract(current_date, contract_start))
                )
                if not is_prev:
                    current_months += 1
                current_date += relativedelta(months=1)

            if current_months > 0:
                monthly_tds = record.tax_pay_ref / current_months
                # Always round up to next whole rupee
                monthly_tds = float(math.ceil(monthly_tds))
                record.tds_deduction_month = monthly_tds
                record.tds_deduction_month_cess = monthly_tds
            else:
                record.tds_deduction_month = 0.0
                record.tds_deduction_month_cess = 0.0

    @api.onchange('tax_pay_ref', 'tds_from_date', 'tds_to_date', 'hr_contract_id', 'previous_employer_from_date', 'previous_employer_to_date', 'prepaid_tds')
    def _onchange_tds_per_year(self):
        """Generate month-wise TDS breakdown showing previous employer months and current employer months."""
        for record in self:
            if record.tds_from_date and record.tds_to_date:
                # Always show full FY months (April to March)
                fy_start = record.tds_from_date
                fy_end = record.tds_to_date
                
                # Get start date for current employer in this FY (earliest contract in FY)
                contract_start = record._get_current_employer_start_date(fy_start, fy_end)

                prev_months = record._count_previous_employer_months(fy_start, fy_end, contract_start)
                monthly_prev = round((record.prepaid_tds or 0.0) / prev_months, 2) if prev_months else 0.0

                monthly_cur = 0.0
                if record.tax_pay_ref:
                    total_months = 0
                    current_date = fy_start
                    prev_from, prev_to = record._get_previous_employer_period_clipped(fy_start, fy_end)
                    while current_date <= fy_end:
                        is_prev = record._is_previous_employer_month(current_date, prev_from, prev_to) if (prev_from and prev_to) else (not record._is_current_employer_month_by_contract(current_date, contract_start))
                        if not is_prev:
                            total_months += 1
                        current_date += relativedelta(months=1)
                    if total_months > 0:
                        monthly_cur = round(record.tax_pay_ref / total_months, 2)

                # Build month list for full FY, marking previous employer months
                month_ids = []
                current_date = fy_start
                prev_from, prev_to = record._get_previous_employer_period_clipped(fy_start, fy_end)
                
                # Generate all months from FY start to FY end
                while current_date <= fy_end:
                    month_name = current_date.strftime("%B")
                    year = current_date.year
                    
                    is_previous = record._is_previous_employer_month(current_date, prev_from, prev_to) if (prev_from and prev_to) else (not record._is_current_employer_month_by_contract(current_date, contract_start))
                    
                    tds_amount = monthly_prev if is_previous else monthly_cur
                    
                    month_ids.append((0, 0, {
                        'months': month_name.lower(),
                        'tds_month_amt': tds_amount,
                        'tds_month_year': f"{month_name} {year}",
                        'is_previous_employer': is_previous
                    }))
                    current_date += relativedelta(months=1)

                # Clear and update month lines
                record.month_ids = [(5, 0, 0)] + month_ids
            else:
                record.month_ids = [(5, 0, 0)]


    @api.depends('tax_payable_cess', 'tax_round_off_amount', 'prepaid_tds')
    def _compute_tax_pay_ref(self):
        for record in self:
            # Include round off amount in the final payable before subtracting prepaid TDS
            record.tax_pay_ref = (record.tax_payable_cess or 0.0) + (record.tax_round_off_amount or 0.0) - (record.prepaid_tds or 0.0)


    @api.depends('deduction_ids', 'deduction_ids.deduction_amt')
    def _compute_grouped_deductions_html(self):
        for record in self:
            grouped = defaultdict(lambda: {"schemes": [], "total": 0, "max_limit": 0})
            combined_limits = defaultdict(lambda: {"sections": [], "total": 0, "max_limit": 0})
            total_deduction_amt = 0  # Initialize total deduction amount
            #
            # # Define combined section groups (e.g., 80C + 80CCD(1) together have a max limit of ₹1,50,000)
            section_groups = {
                "80C": ["80C", "80CCC", "80CCD(1)"],  # These sections share a limit of ₹1,50,000
            }

            # Step 1: Group schemes under each section
            current_regime = record.tax_regime_type
            valid_lines = record.deduction_ids
            if current_regime:
                valid_lines = valid_lines.filtered(lambda l: (l.tax_regime_type or current_regime) == current_regime)

            for line in valid_lines:
                section_name = line.section_id.name
                grouped[section_name]["schemes"].append(
                    {"name": line.scheme_id.scheme_name, "amount": line.deduction_amt})
                grouped[section_name]["total"] += line.deduction_amt
                grouped[section_name]["max_limit"] = line.max_limit_deduction  # Ensure this field exists
                # total_deduction_amt += line.deduction_amt
            # Step 2: Handle combined limits
            combined_vals = list(itertools.chain(*section_groups.values()))
            if set(combined_vals) & set(valid_lines.section_id.mapped('name')):
                for group_name, sections in section_groups.items():
                    total_combined = sum(grouped[sec]["total"] if sec in grouped else 0 for sec in sections)
                    # total_deduction_amt -= total_combined,
                    max_limit_combined = min(grouped[sec]["max_limit"] for sec in sections if sec in grouped)
                    total_deduction_amt += min(total_combined, max_limit_combined)  # Ensure it doesn't exceed max limit

            for line in valid_lines:
                section_name = line.section_id.name
                if section_name not in combined_vals:
                    total_deduction_amt += min(line.max_limit_deduction, line.deduction_amt) if line.scheme_id.type_of_deduction == 'amount' else line.deduction_amt


            # Step 3: Assign total deduction amount to the field
            record.total_deductions = total_deduction_amt

            # Step 4: Build HTML output
            html_content = "<div class='deduction-summary'>"
            for section, data in grouped.items():
                html_content += f"""
                 <div class='section'>
                     <strong>Section {section}:</strong>
                     <div class='scheme-list'>
                 """
                for scheme in data["schemes"]:
                    html_content += f"""
                         <div class='scheme'>
                             <span>{scheme['name']}:</span>
                             <span class='amount'>{scheme['amount']}</span>
                         </div>
                     """

                html_content += f"""
                     </div>
                     <hr/>
                     <div class='max-limit'>
                         <span>Max Limit ({data['max_limit']})</span>
                         <span class='amount'>{data['total']}</span>
                     </div>
                 </div>
                 """

            html_content += "</div>"

            # Assign the final HTML to the field
            record.grouped_deductions_html = html_content

    @api.depends(
        'deduction_ids',
        'deduction_ids.section_id',
        'deduction_ids.scheme_id',
        'deduction_ids.deduction_amt',
        'deduction_ids.max_limit_deduction',
        'deduction_ids.scheme_id.type_of_deduction',
        'total_deductions',
        'tax_regime_type',
    )
    def _compute_deduction_summary_html(self):
        for record in self:
            lines = []
            current_regime = record.tax_regime_type
            valid_lines = record.deduction_ids
            if current_regime:
                valid_lines = valid_lines.filtered(lambda l: (l.tax_regime_type or current_regime) == current_regime)

            # Group by Section -> [(scheme_name, amount)]
            from collections import OrderedDict
            sections = OrderedDict()
            for line in valid_lines:
                if not line.scheme_id or not line.section_id:
                    continue
                amount = line.deduction_amt or 0.0
                if line.scheme_id.type_of_deduction == 'amount' and (line.max_limit_deduction or 0.0) > 0.0:
                    amount = min(amount, line.max_limit_deduction)
                if amount <= 0.0:
                    continue

                section_name = (line.section_id.name or '').strip() or 'Other'
                scheme_name = (line.scheme_id.scheme_name or '').strip()
                if section_name not in sections:
                    sections[section_name] = []
                sections[section_name].append((scheme_name, amount))

            if not sections:
                record.deduction_summary_html = ""
                continue

            # Flex-based grouped list: Section header then a second line with schemes and amounts
            html = "<div class='o_tdss_deduction_summary' style='width:100%; overflow:hidden;'>"
            html += "<ul class='tds-ded-list' style='list-style:none; padding:0; margin:0;'>"
            for sec, items in sections.items():
                safe_sec = sec.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                sec_total = sum(a for _, a in items)
                # Section header row: Section name on left, subtotal on right
                html += (
                    "<li class='tds-ded-sec' "
                    "style='display:flex; align-items:flex-start; justify-content:space-between; gap:8px; padding:6px 0 2px; line-height:1.25; font-weight:600; border-top:1px solid #e5e7eb;'>"
                    f"<span class='tds-ded-sec-label' style='flex:1; min-width:0; white-space:normal; overflow-wrap:anywhere; word-break:normal;'>{safe_sec}</span>"
                    f"<span class='tds-ded-sec-amount' style='white-space:nowrap; text-align:right;'>{sec_total:,.2f}</span>"
                    "</li>"
                )
                # Second part: each scheme on its own line under the section
                for sch, amt in items:
                    safe_s = sch.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    html += (
                        "<li class='tds-ded-sec-item' "
                        "style='display:flex; align-items:flex-start; gap:8px; padding:2px 0; line-height:1.3;'>"
                        f"<span class='tds-ded-scheme' style='flex:1; min-width:0; white-space:normal; overflow-wrap:anywhere; word-break:normal; hyphens:auto; color:#4b5563;'>{safe_s}</span>"
                        f"<span class='tds-ded-amount' style='white-space:nowrap; text-align:right;'>{amt:,.2f}</span>"
                        "</li>"
                    )

            total = record.total_deductions or 0.0
            html += "</ul>"
            html += (
                "<div class='tds-ded-total' "
                "style='display:flex; align-items:center; justify-content:space-between; gap:8px; border-top:1px solid #ddd; margin-top:6px; padding-top:6px; font-weight:600;'>"
                "<span>Total Deductions</span>"
                f"<span class='tds-ded-amount' style='white-space:nowrap;'>{total:,.2f}</span>"
                "</div>"
            )
            html += "</div>"
            record.deduction_summary_html = html

    @api.depends(
        'deduction_ids',
        'deduction_ids.section_id',
        'deduction_ids.scheme_id',
        'deduction_ids.deduction_amt',
        'deduction_ids.max_limit_deduction',
        'deduction_ids.scheme_id.type_of_deduction',
    )
    def _compute_total_deductions(self):
        for record in self:
            total_deduction_amt = 0
            section_groups = {
                "80C": ["80C", "80CCC", "80CCD(1)"],
            }

            grouped_totals = defaultdict(lambda: {"total": 0.0, "max_limit": 0.0})
            allowed_scheme_ids = set((record.available_scheme_ids or record.env['tds.section.scheme']).ids)
            allowed_section_ids = set((record.available_section_ids or record.env['tds.section']).ids)
            current_regime = record.tax_regime_type
            valid_lines = record.deduction_ids.filtered(lambda l: l.scheme_id and (l.scheme_id.id in allowed_scheme_ids))
            if current_regime:
                valid_lines = valid_lines.filtered(lambda l: (l.tax_regime_type or current_regime) == current_regime)
            for line in valid_lines:
                section_name = line.section_id.name
                grouped_totals[section_name]["total"] += (line.deduction_amt or 0.0)
                grouped_totals[section_name]["max_limit"] = line.max_limit_deduction

            combined_vals = list(itertools.chain(*section_groups.values()))
            if set(combined_vals) & set(valid_lines.section_id.mapped('name')):
                for group_name, sections in section_groups.items():
                    total_combined = sum(grouped_totals[sec]["total"] if sec in grouped_totals else 0.0 for sec in sections)
                    max_limit_candidates = [grouped_totals[sec]["max_limit"] for sec in sections if sec in grouped_totals]
                    max_limit_combined = min(max_limit_candidates) if max_limit_candidates else 0.0
                    total_deduction_amt += min(total_combined, max_limit_combined) if max_limit_combined else total_combined

            for line in valid_lines:
                section_name = line.section_id.name
                if section_name in combined_vals:
                    continue
                if line.scheme_id and line.scheme_id.type_of_deduction == 'amount':
                    total_deduction_amt += min(line.max_limit_deduction, line.deduction_amt) if line.max_limit_deduction else (line.deduction_amt or 0.0)
                else:
                    total_deduction_amt += (line.deduction_amt or 0.0)

            record.total_deductions = total_deduction_amt



    @api.depends('other_income_ids', 'other_income_ids.net_taxable_amount')
    def _compute_total_other_income(self):
        for tds in self:
            tds.total_other_income = sum(tds.other_income_ids.mapped('net_taxable_amount'))

    @api.depends(
        'income_chargeable_salaries',
        'tax_regime_slab',
        'total_other_income',
        'total_exemptions_10',
        'total_hra_exemption',
        'total_deductions',
    )
    def _compute_tax_slab(self):
        for tds in self:
            # Include previous employer taxable amount and other income for comprehensive tax calculation
            total_annual_income = (tds.income_chargeable_salaries or 0.0) + (tds.total_other_income or 0.0)
            total_exemptions = (tds.total_exemptions_10 or 0.0) + (tds.total_hra_exemption or 0.0)
            total_deductions = (tds.total_deductions or 0.0)
            tds.taxable_amount = float(max(total_annual_income - total_exemptions - total_deductions, 0.0))

    # NOTE: round-off amount is now a manual field set by user as per requirement.

    def _get_tax_amounts_from_slabs(self, annual_income):
        self.ensure_one()
        if not self.tax_regime_slab:
            return 0.0, 0.0, 0.0, 0.0

        annual_income = max(annual_income or 0.0, 0.0)
        total_tax = 0.0
        slabs = self.tax_regime_slab.tax_regime_line_ids
        prev_upper = 0.0
        applied_surcharge_rate = 0.0
        applied_surcharge_threshold = 0.0
        prev_surcharge_rate = 0.0
        for slab in slabs.sorted(lambda s: s.tax_regime_amt_from):
            # compute effective lower bound as max(slab.from, previous upper)
            slab_from = slab.tax_regime_amt_from or 0.0
            slab_to = slab.tax_regime_amt_to or 0.0
            lower = max(slab_from, prev_upper)
            # Normalize off-by-one gaps in configured slabs (e.g., 400001 after 400000)
            if abs((slab_from or 0.0) - (prev_upper or 0.0) - 1.0) < 1e-6:
                lower = prev_upper
            if annual_income <= lower:
                break
            upper = slab_to if slab_to and slab_to > 0.0 else annual_income
            upper = min(upper, annual_income)
            taxable_income = max(upper - lower, 0.0)
            if taxable_income:
                slab_tax = (taxable_income * (slab.tax_regime_per or 0.0)) / 100
                total_tax += slab_tax

                # Determine surcharge slab (single rate applies based on final income slab).
                # We treat the last applicable slab's `surcharge` as the surcharge rate.
                slab_surcharge_rate = float(slab.surcharge or 0.0)
                if slab_surcharge_rate != prev_surcharge_rate:
                    applied_surcharge_threshold = float(lower or 0.0)
                    prev_surcharge_rate = slab_surcharge_rate
                applied_surcharge_rate = slab_surcharge_rate
            prev_upper = upper

        # Helper: ceil only when fractional part exists (never round down)
        def _ceil_if_fraction(val: float):
            v = float(val or 0.0)
            return math.ceil(v) if not float(v).is_integer() else float(v)

        # Base tax (no surcharge) with ceil-if-fraction
        base_tax = _ceil_if_fraction(total_tax)

        # Single slab surcharge (not progressive) using ceil-if-fraction
        surcharge_amount = _ceil_if_fraction((base_tax * applied_surcharge_rate) / 100.0) if base_tax else 0.0
        tax_with_surcharge = _ceil_if_fraction(base_tax + surcharge_amount)

        # Marginal relief at surcharge slab jumps
        if applied_surcharge_rate and applied_surcharge_threshold and annual_income > applied_surcharge_threshold:
            # Compute tax at threshold using previous surcharge rate (i.e., rate before jump)
            threshold_income = float(applied_surcharge_threshold)
            threshold_base_tax, threshold_tax_with_surcharge, _, _ = self._get_tax_amounts_from_slabs(
                threshold_income
            )
            # threshold_tax_with_surcharge is already base + surcharge at threshold
            allowed_extra = annual_income - threshold_income
            actual_extra = tax_with_surcharge - threshold_tax_with_surcharge
            if actual_extra > allowed_extra:
                tax_with_surcharge = _ceil_if_fraction(threshold_tax_with_surcharge + allowed_extra)
                surcharge_amount = max(_ceil_if_fraction(tax_with_surcharge - base_tax), 0.0)

        # Education cess is 4% on tax; apply ceil-if-fraction
        education_cess = _ceil_if_fraction((tax_with_surcharge * 4) / 100)
        tax_with_cess = tax_with_surcharge + education_cess

        return base_tax, tax_with_surcharge, tax_with_cess, surcharge_amount

    def _recompute_tax_payable_fields(self):
        for rec in self:
            base_tax, tax, tax_with_cess, surcharge_amount = rec._get_tax_amounts_from_slabs(rec.taxable_amount)
            rec.surcharge = surcharge_amount

            # Apply rebate u/s 87A if configured on slab and income is within limit.
            applied_rebate = 0.0
            if rec.tax_regime_slab and rec.tax_regime_slab.enable_rebate_87a:
                limit_amt = float(rec.tax_regime_slab.rebate_87a_income_limit or 0.0)
                rebate_amt = float(rec.tax_regime_slab.rebate_87a_amount or 0.0)
                if limit_amt and (rec.taxable_amount or 0.0) <= limit_amt and rebate_amt and tax:
                    applied_rebate = min(rebate_amt, float(tax))

            tax_after_rebate = max(float(tax or 0.0) - float(applied_rebate or 0.0), 0.0)
            cess_after_rebate = round((tax_after_rebate * 4) / 100) if tax_after_rebate else 0.0
            rec.rebate_87a = applied_rebate
            rec.tax_payable = tax_after_rebate
            rec.health_education_cess = cess_after_rebate
            rec.tax_payable_cess = tax_after_rebate + cess_after_rebate



    @api.onchange('annual_salary', 'taxable_amount', 'tax_regime_slab', 'total_deductions', 'previous_employer_taxable', 'deduction_ids')
    def _onchange_annual_salary(self):
        """
        Calculate tax payable based on total annual income including previous employer.
        This ensures accurate TDS calculation for employees who changed companies mid-year.
        """
        for tds in self:
            if not tds.tax_regime_slab:
                tds.tax_payable = 0
                tds.tax_payable_cess = 0
                continue

            # Trigger recomputation of deductions and taxable amount
            tds._compute_grouped_deductions_html()
            tds._compute_total_exemptions_10()
            tds._compute_income_chargeable_salaries()
            tds._compute_total_other_income()
            tds._compute_tax_slab()
            
            # Use taxable_amount which now includes previous employer income and deductions
            base_tax, tax, tax_with_cess, surcharge_amount = tds._get_tax_amounts_from_slabs(tds.taxable_amount)
            tds.surcharge = surcharge_amount

            applied_rebate = 0.0
            if tds.tax_regime_slab and tds.tax_regime_slab.enable_rebate_87a:
                limit_amt = float(tds.tax_regime_slab.rebate_87a_income_limit or 0.0)
                rebate_amt = float(tds.tax_regime_slab.rebate_87a_amount or 0.0)
                if limit_amt and (tds.taxable_amount or 0.0) <= limit_amt and rebate_amt and tax:
                    applied_rebate = min(rebate_amt, float(tax))

            tax_after_rebate = max(float(tax or 0.0) - float(applied_rebate or 0.0), 0.0)
            cess_after_rebate = round((tax_after_rebate * 4) / 100) if tax_after_rebate else 0.0
            tds.rebate_87a = applied_rebate
            tds.tax_payable = tax_after_rebate
            tds.health_education_cess = cess_after_rebate
            tds.tax_payable_cess = tax_after_rebate + cess_after_rebate
            # tds.tds_deduction_month_cess = round(tds.tax_payable_cess / 12)

    @api.depends(
        'taxable_amount',
        'tax_regime_slab',
        'tax_regime_slab.enable_rebate_87a',
        'tax_regime_slab.rebate_87a_income_limit',
        'tax_regime_slab.rebate_87a_amount',
        'tax_regime_slab.tax_regime_line_ids',
        'tax_regime_slab.tax_regime_line_ids.tax_regime_amt_from',
        'tax_regime_slab.tax_regime_line_ids.tax_regime_amt_to',
        'tax_regime_slab.tax_regime_line_ids.tax_regime_per',
        'tax_regime_slab.tax_regime_line_ids.surcharge',
        'tax_round_off_amount',
        'rebate_87a'
    )
    def _compute_tax_breakdown_html(self):
        for rec in self:
            if not rec.tax_regime_slab:
                rec.tax_breakdown_html = ''
                continue

            income = rec.taxable_amount or 0.0
            if income <= 0:
                rec.tax_breakdown_html = ''
                continue

            rows = []
            total_tax = 0.0
            slabs = rec.tax_regime_slab.tax_regime_line_ids
            prev_upper = 0.0
            for slab in slabs.sorted(lambda s: s.tax_regime_amt_from):
                slab_from = slab.tax_regime_amt_from or 0.0
                slab_to = slab.tax_regime_amt_to or 0.0
                lower = max(slab_from, prev_upper)
                # Normalize off-by-one gaps in configured slabs (e.g., 400001 after 400000)
                if abs((slab_from or 0.0) - (prev_upper or 0.0) - 1.0) < 1e-6:
                    lower = prev_upper
                if income <= lower:
                    break
                upper = slab_to if slab_to and slab_to > 0.0 else income
                upper = min(upper, income)
                slab_amount = max(upper - lower, 0.0)
                if slab_amount <= 0:
                    prev_upper = upper
                    continue
                rate = slab.tax_regime_per or 0.0
                slab_tax = (slab_amount * rate) / 100.0
                total_tax += slab_tax
                rows.append((lower, upper if slab_to else None, slab_amount, rate, slab_tax))
                prev_upper = upper

            base_tax, tax_with_surcharge, tax_with_cess, surcharge_amount = rec._get_tax_amounts_from_slabs(income)

            applied_rebate = 0.0
            if rec.tax_regime_slab and rec.tax_regime_slab.enable_rebate_87a:
                limit_amt = float(rec.tax_regime_slab.rebate_87a_income_limit or 0.0)
                rebate_amt = float(rec.tax_regime_slab.rebate_87a_amount or 0.0)
                if limit_amt and (income or 0.0) <= limit_amt and rebate_amt and tax_with_surcharge:
                    applied_rebate = min(rebate_amt, float(tax_with_surcharge))

            tax_after_rebate = max(float(tax_with_surcharge or 0.0) - float(applied_rebate or 0.0), 0.0)
            cess = round((tax_after_rebate * 4) / 100) if tax_after_rebate else 0.0
            total_with_cess = tax_after_rebate + cess
            # Use manual round-off amount
            round_off = float(rec.tax_round_off_amount or 0.0)
            total_after_round = total_with_cess + round_off

            html = []
            html.append("<div class='o_tdss_tax_breakdown' style='width:100%;'>")
            html.append("<table class='table table-sm table-borderless mb-0' style='width:100%;'>")
            html.append("<colgroup><col style='width:55%'><col style='width:15%'><col style='width:15%'><col style='width:15%'></colgroup>")
            html.append("<thead><tr><th style='text-align:left; white-space:nowrap;'>Slab</th><th class='text-end' style='white-space:nowrap;'>Amount</th><th class='text-end' style='white-space:nowrap;'>Rate</th><th class='text-end' style='white-space:nowrap;'>Tax</th></tr></thead>")
            html.append("<tbody>")
            # Helper: ceil only when value has a fractional component
            def _ceil_if_fraction(val):
                try:
                    v = float(val or 0.0)
                    return math.ceil(v) if not float(v).is_integer() else v
                except Exception:
                    return val or 0.0
            for frm, up, amt, rate, tax in rows:
                slab_label = f"{int(frm):,} - {(int(up) if up is not None else '∞')}"
                html.append(
                    "<tr>"
                    f"<td style='white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>{slab_label}</td>"
                    f"<td class='text-end' style='white-space:nowrap;'>{_ceil_if_fraction(amt):,}</td>"
                    f"<td class='text-end' style='white-space:nowrap;'>{rate:.0f}%</td>"
                    f"<td class='text-end' style='white-space:nowrap;'>{_ceil_if_fraction(tax):,}</td>"
                    "</tr>"
                )
            html.append("</tbody>")
            html.append("<tfoot>")
            html.append(
                "<tr style='border-top:1px solid #ddd;'>"
                "<td colspan='3' style='font-weight:600;'>Base Tax</td>"
                f"<td class='text-end' style='font-weight:600;'>{_ceil_if_fraction(base_tax):,}</td>"
                "</tr>"
            )
            html.append(
                "<tr>"
                "<td colspan='3'>Surcharge</td>"
                f"<td class='text-end'>{_ceil_if_fraction(float(surcharge_amount or 0.0)):,}</td>"
                "</tr>"
            )
            html.append(
                "<tr>"
                "<td colspan='3' style='font-weight:600;'>Tax (Base + Surcharge)</td>"
                f"<td class='text-end' style='font-weight:600;'>{_ceil_if_fraction(tax_with_surcharge):,}</td>"
                "</tr>"
            )
            if applied_rebate:
                html.append(
                    "<tr>"
                    "<td colspan='3'>Rebate u/s 87A</td>"
                    f"<td class='text-end'>-{_ceil_if_fraction(float(applied_rebate or 0.0)):,}</td>"
                    "</tr>"
                )
            html.append(
                "<tr>"
                "<td colspan='3'>Education Cess (4%)</td>"
                f"<td class='text-end'>{_ceil_if_fraction(cess):,}</td>"
                "</tr>"
            )
            html.append(
                "<tr>"
                "<td colspan='3'>Round Off (to nearest 10)</td>"
                f"<td class='text-end'>{round_off:,}</td>"
                "</tr>"
            )
            html.append(
                "<tr>"
                "<td colspan='3' style='font-weight:600;'>Total Tax</td>"
                f"<td class='text-end' style='font-weight:600;'>{_ceil_if_fraction(total_after_round):,}</td>"
                "</tr>"
            )
            html.append("</tfoot>")
            html.append("</table></div>")
            rec.tax_breakdown_html = ''.join(html)


    @api.model_create_multi
    def create(self, vals_list):
        """Set hr_employee_id from hr_contract_id when missing, then create."""
        for vals in vals_list:
            if not vals.get('hr_employee_id') and vals.get('hr_contract_id'):
                contract = self.env['hr.contract'].browse(vals['hr_contract_id'])
                if contract.employee_id:
                    vals['hr_employee_id'] = contract.employee_id.id
        res = super(HrTDS, self).create(vals_list)
        if res and not any(k in (vals_list[0] if vals_list else {}) for k in ['tax_payable', 'tax_payable_cess']):
            res._recompute_tax_payable_fields()
        if res:
            res._sync_month_ids_lines()
        return res
        if not any(k in (vals[0] if vals else {}) for k in ['tax_payable', 'tax_payable_cess']):
            res._recompute_tax_payable_fields()
        res._sync_month_ids_lines()
        # if res.is_tds_payslip:
        #     # Set all other records' boolean_field to False for the same employee
        #     self.search([
        #         ('hr_employee_id', '=', res.hr_employee_id.id),
        #         ('id', '!=', res.id)
        #     ]).write({'is_tds_payslip': False})
        return res

    def write(self, vals):
        """Ensure only one True value per employee_id during updates and trigger recalculation."""
        res = super(HrTDS, self).write(vals)

        if any(key in vals for key in ['annual_salary', 'prepaid_tds', 'tax_payable_cess', 'deduction_ids', 'previous_employer_taxable', 'hr_contract_id', 'other_income_ids']):
            for record in self:
                record._compute_grouped_deductions_html()
                record._compute_monthly_tds()

        if not any(k in vals for k in ['tax_payable', 'tax_payable_cess']) and any(
            k in vals for k in [
                'annual_salary',
                'tax_regime_slab',
                'deduction_ids',
                'previous_employer_taxable',
                'other_income_ids',
                'rent_payment_ids',
                'use_multiple_rent_periods',
                'basic_salary',
                'actual_rental_paid',
                'hra_received',
                'rent_excess_per',
                'hra_per',
                'standard_deduction_16_ii',
                'perquisites_17_2',
                'profits_17_3',
                'travel_concession_10_5',
                'gratuity_10_10',
                'commuted_pension_10_10a',
                'leave_salary_10_10aa',
                'other_exemptions_10',
                'tax_regime_type',
            ]
        ):
            self._recompute_tax_payable_fields()

        if not self.env.context.get('skip_month_sync'):
            self._sync_month_ids_lines()
        # if 'is_tds_payslip' in vals and vals['is_tds_payslip']:
        #     for record in self:
        #         # Set all other records' boolean_field to False for the same employee
        #         self.search([
        #             ('hr_employee_id', '=', record.hr_employee_id.id),
        #             ('id', '!=', record.id)
        #         ]).write({'is_tds_payslip': False})
        return res

    def action_recompute_tds(self):
        """
        Manual recompute trigger to refresh all TDS-related computed values on demand.
        Applies all exemptions and deductions to calculate accurate taxable income.
        """
        for rec in self:
            rec._sync_salary_increments_from_contracts()
            rec._sync_hra_from_contract()
            rec._compute_annual_salary()
            rec._compute_total_other_income()
            rec._compute_total_exemptions_10()
            rec._compute_total_hra_exemption()
            rec._compute_income_chargeable_salaries()
            rec._compute_total_deductions()
            rec._compute_grouped_deductions_html()
            rec._compute_tax_slab()
            rec._recompute_tax_payable_fields()
            rec._compute_monthly_tds()
            rec._compute_monthly_breakdown_html()
            rec._sync_month_ids_lines()
        return True

    @api.onchange('tax_round_off_amount')
    def _onchange_tax_round_off_amount(self):
        """Instantly reflect manual round-off in totals and monthly view while editing."""
        for rec in self:
            rec._compute_tax_pay_ref()
            rec._compute_monthly_tds()
            rec._compute_monthly_breakdown_html()

    @api.onchange('tax_regime_slab')
    def _onchange_tax_regime_slab_reset_deductions(self):
        for rec in self:
            if not rec.tax_regime_slab:
                continue

            allowed_scheme_ids = set((rec.available_scheme_ids or self.env['tds.section.scheme']).ids)
            allowed_section_ids = set((rec.available_section_ids or self.env['tds.section']).ids)

            prev_type = rec._origin.tax_regime_type
            if prev_type in ('old', 'new'):
                cache = []
                for line in rec.deduction_ids:
                    cache.append({
                        'section_id': line.section_id.id if line.section_id else False,
                        'scheme_id': line.scheme_id.id if line.scheme_id else False,
                        'deduction_amt': line.deduction_amt or 0.0,
                    })
                if prev_type == 'old':
                    rec.deduction_cache_old = json.dumps(cache)
                else:
                    rec.deduction_cache_new = json.dumps(cache)

            for line in rec.deduction_ids:
                invalid_scheme = bool(allowed_scheme_ids) and line.scheme_id and (line.scheme_id.id not in allowed_scheme_ids)
                invalid_section = bool(allowed_section_ids) and line.section_id and (line.section_id.id not in allowed_section_ids)
                if invalid_scheme or invalid_section:
                    line.scheme_id = False
                    line.section_id = False
                    line.deduction_amt = 0.0

            cur_type = rec.tax_regime_type
            load_json = rec.deduction_cache_old if cur_type == 'old' else (rec.deduction_cache_new if cur_type == 'new' else False)
            if load_json:
                try:
                    data = json.loads(load_json) or []
                except Exception:
                    data = []
                cmds = [(5, 0, 0)]
                for item in data:
                    sid = item.get('scheme_id') or False
                    secid = item.get('section_id') or False
                    amt = item.get('deduction_amt') or 0.0
                    if sid and sid in allowed_scheme_ids:
                        cmds.append((0, 0, {
                            'scheme_id': sid,
                            'section_id': secid if (not secid or secid in allowed_section_ids) else False,
                            'deduction_amt': amt,
                        }))
                if len(cmds) > 1:
                    rec.deduction_ids = cmds

            # Recompute values in-memory so the user sees updated amounts immediately.
            rec._compute_total_deductions()
            rec._compute_grouped_deductions_html()
            rec._compute_total_exemptions_10()
            rec._compute_total_hra_exemption()
            rec._compute_income_chargeable_salaries()
            rec._compute_total_other_income()
            rec._compute_tax_slab()
            rec._recompute_tax_payable_fields()
            rec._compute_monthly_tds()
            rec._compute_monthly_breakdown_html()

    def action_print_tds_details(self):
        """Print full TDS details (income, tax, monthly split) as PDF."""
        self.ensure_one()
        report_action = None
        try:
            report_action = self.env.ref('hr_contract_extension.action_report_tds_details')
        except Exception:
            report_action = None

        if not report_action:
            report_action = self.env['ir.actions.report'].search([
                ('report_name', '=', 'hr_contract_extension.report_tds_details'),
            ], limit=1)

        if not report_action:
            raise ValueError(
                "TDS report action not found. Please upgrade module 'hr_contract_extension' to load reports/tds_report.xml. "
                "Missing XMLID: hr_contract_extension.action_report_tds_details"
            )

        return report_action.report_action(self)
