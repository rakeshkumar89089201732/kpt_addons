from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    tds_engine_tds_id = fields.Many2one('hr.tds', string='TDS Engine Record', compute='_compute_tds_engine', store=True)
    tds_engine_projected_income = fields.Float(string='Projected Annual Income', compute='_compute_tds_engine', store=True)
    tds_engine_annual_tax = fields.Float(string='Annual Tax (with Cess)', compute='_compute_tds_engine', store=True)
    tds_engine_tds_deducted_till_date = fields.Float(string='TDS Deducted Till Date', compute='_compute_tds_engine', store=True)
    tds_engine_remaining_tax = fields.Float(string='Remaining Tax', compute='_compute_tds_engine', store=True)
    tds_engine_remaining_months = fields.Integer(string='Remaining Payroll Months', compute='_compute_tds_engine', store=True)
    tds_engine_monthly_tds = fields.Float(string='Monthly TDS (This Payslip)', compute='_compute_tds_engine', store=True)

    def compute_sheet(self):
        """Ensure TDS engine values are fresh before salary rules run.

        Problem: these fields are stored computed fields that only depend on
        payslip dates/employee/contract. When the user updates the TDS record,
        the payslip won't automatically recompute them, so the TDS salary rule
        condition won't trigger and TDS won't appear on the payslip/print.
        """
        # Force recompute of the stored computed fields so salary rules can use them.
        # (Works even if only the hr.tds record changed.)
        self._compute_tds_engine()
        return super().compute_sheet()

    def _get_tds_engine_record(self):
        self.ensure_one()
        Tds = self.env['hr.tds']
        employee_id = self.employee_id.id
        contract_id = self.contract_id.id if self.contract_id else False
        date_from = self.date_from

        def _date_domain():
            if not date_from:
                return []
            return [
                ('tds_from_date', '<=', date_from),
                ('tds_to_date', '>=', date_from),
            ]

        # 1) By employee + is_tds_payslip + date range
        domain = [
            ('hr_employee_id', '=', employee_id),
            ('is_tds_payslip', '=', True),
        ] + _date_domain()
        tds = Tds.search(domain, order='tds_from_date desc, id desc', limit=1)
        if tds:
            return tds

        # 2) By employee + date range (any is_tds_payslip)
        if date_from:
            tds = Tds.search([
                ('hr_employee_id', '=', employee_id),
                ('tds_from_date', '<=', date_from),
                ('tds_to_date', '>=', date_from),
            ], order='tds_from_date desc, id desc', limit=1)
            if tds:
                return tds

        # 3) By contract (TDS may have only hr_contract_id set) + is_tds_payslip + date range
        if contract_id:
            domain_contract = [
                ('hr_contract_id', '=', contract_id),
                ('is_tds_payslip', '=', True),
            ] + _date_domain()
            tds = Tds.search(domain_contract, order='tds_from_date desc, id desc', limit=1)
            if tds:
                return tds

        # 4) By contract + date range (any is_tds_payslip)
        if contract_id and date_from:
            tds = Tds.search([
                ('hr_contract_id', '=', contract_id),
                ('tds_from_date', '<=', date_from),
                ('tds_to_date', '>=', date_from),
            ], order='tds_from_date desc, id desc', limit=1)
            if tds:
                return tds

        # 5) By employee + is_tds_payslip (no date filter)
        tds = Tds.search([
            ('hr_employee_id', '=', employee_id),
            ('is_tds_payslip', '=', True),
        ], order='tds_from_date desc, id desc', limit=1)
        if tds:
            return tds

        # 6) By employee only (no date, no is_tds_payslip requirement) - most lenient
        tds = Tds.search([
            ('hr_employee_id', '=', employee_id),
        ], order='tds_from_date desc, id desc', limit=1)
        if tds:
            return tds

        # 7) Last: by contract only (e.g. TDS with no dates or only hr_contract_id)
        if contract_id:
            tds = Tds.search([
                ('hr_contract_id', '=', contract_id),
                ('is_tds_payslip', '=', True),
            ], order='tds_from_date desc, id desc', limit=1)
            if tds:
                return tds
            # Even more lenient: contract without is_tds_payslip requirement
            return Tds.search([
                ('hr_contract_id', '=', contract_id),
            ], order='tds_from_date desc, id desc', limit=1)

        return Tds.browse()

    def _get_fy_range_for_payslip(self):
        self.ensure_one()
        tds = self._get_tds_engine_record()
        if tds and tds.tds_from_date and tds.tds_to_date:
            return tds.tds_from_date, tds.tds_to_date
        # Fallback to April-March based on payslip date
        ref_date = self.date_from or fields.Date.today()
        year = ref_date.year
        if ref_date.month < 4:
            year -= 1
        return fields.Date.to_date(f'{year}-04-01'), fields.Date.to_date(f'{year + 1}-03-31')

    def _get_tds_deducted_from_payslips(self, fy_start, payslip_period_start):
        self.ensure_one()
        # Sum already validated payslips' TDS line amounts (absolute) within FY, before current payslip period.
        # This ensures we never recompute tax per month; we only adjust remaining liability.
        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('state', 'in', ['done', 'paid']),
            ('date_from', '>=', fy_start),
            ('date_from', '<', payslip_period_start),
            ('credit_note', '=', False),
        ]
        payslips = self.env['hr.payslip'].search(domain)
        if not payslips:
            return 0.0
        # Salary rule code for TDS will be 'TDS'.
        tds_lines = payslips.mapped('line_ids').filtered(lambda l: l.code == 'TDS')
        return sum(abs(l.total or 0.0) for l in tds_lines)

    def _compute_remaining_months(self, fy_end):
        self.ensure_one()
        if not self.date_from or not fy_end or self.date_from > fy_end:
            return 0
        delta = relativedelta(fy_end, self.date_from)
        months = (delta.years * 12) + delta.months + 1
        return max(months, 0)

    def _get_tds_deducted_from_paid_periods(self, tds, fy_start, payslip_period_start):
        self.ensure_one()
        if not tds or not (tds.use_paid_tds_periods or tds.paid_tds_period_ids) or not tds.paid_tds_period_ids:
            return 0.0
        if not payslip_period_start:
            return 0.0

        # Count paid-period amounts for months strictly before current payslip month.
        cutoff_month_start = payslip_period_start.replace(day=1)
        total = 0.0
        for p in tds.paid_tds_period_ids:
            if not p.period_from or not p.period_to or p.period_from > p.period_to:
                continue

            # Build the full month list for this paid period (clipped to FY).
            full_from = max(p.period_from, fy_start)
            full_to = p.period_to
            if full_from > full_to:
                continue

            full_months = []
            cur = full_from.replace(day=1)
            end = full_to.replace(day=1)
            while cur <= end:
                full_months.append(cur)
                cur += relativedelta(months=1)
            if not full_months:
                continue

            per_month = float(p.amount or 0.0) / float(len(full_months))
            months_before_cutoff = [m for m in full_months if m < cutoff_month_start]
            total += per_month * float(len(months_before_cutoff))

        return float(total or 0.0)

    def _get_tds_deducted_from_paid_months(self, tds, fy_start, payslip_period_start):
        self.ensure_one()
        if not tds or not tds.paid_tds_month_ids or not payslip_period_start:
            return 0.0
        cutoff_month_start = payslip_period_start.replace(day=1)
        total = 0.0
        for m in tds.paid_tds_month_ids:
            if not m.month_date:
                continue
            if m.month_date < fy_start:
                continue
            if m.month_date.replace(day=1) >= cutoff_month_start:
                continue
            total += float(m.amount or 0.0)
        return float(total or 0.0)

    @api.depends('employee_id', 'contract_id', 'date_from', 'date_to')
    def _compute_tds_engine(self):
        for slip in self:
            slip.tds_engine_tds_id = False
            slip.tds_engine_projected_income = 0.0
            slip.tds_engine_annual_tax = 0.0
            slip.tds_engine_tds_deducted_till_date = 0.0
            slip.tds_engine_remaining_tax = 0.0
            slip.tds_engine_remaining_months = 0
            slip.tds_engine_monthly_tds = 0.0

            if not slip.employee_id or not slip.date_from:
                continue

            tds = slip._get_tds_engine_record()
            if not tds:
                continue

            # Ensure TDS record is up-to-date.
            # Recompute projected income and annual tax based on current declarations.
            tds._compute_total_other_income()
            tds._compute_total_deductions()
            tds._compute_tax_slab()
            tds._recompute_tax_payable_fields()
            tds._compute_tax_pay_ref()

            fy_start, fy_end = slip._get_fy_range_for_payslip()
            remaining_months = slip._compute_remaining_months(fy_end)

            # Annual tax is computed on full FY projected income (incl. round off).
            annual_tax = (tds.tax_payable_cess or 0.0) + (tds.tax_round_off_amount or 0.0)

            # TDS already deducted till date = previous employer prepaid + current employer deductions
            # If the user maintains paid periods manually, treat that as the authoritative source
            # to avoid double counting and to support non-uniform deductions after increments.
            if tds.paid_tds_month_ids:
                tds_from_current = slip._get_tds_deducted_from_paid_months(tds, fy_start, slip.date_from)
            elif tds.use_paid_tds_periods or tds.paid_tds_period_ids:
                tds_from_current = slip._get_tds_deducted_from_paid_periods(tds, fy_start, slip.date_from)
            else:
                tds_from_current = slip._get_tds_deducted_from_payslips(fy_start, slip.date_from)
            deducted_till_date = (tds.prepaid_tds or 0.0) + (tds_from_current or 0.0)

            remaining_tax = max(annual_tax - deducted_till_date, 0.0)
            # Prefer the fixed "Monthly TDS" computed on the TDS record, if present.
            # This matches the user's expectation: deduct configured monthly TDS, not annual-tax/remaining-months.
            configured_monthly = float(getattr(tds, 'tds_deduction_month_cess', 0.0) or 0.0)
            if configured_monthly > 0.0:
                monthly_tds = configured_monthly
                # In the last month, do not deduct more than the remaining tax.
                if remaining_tax > 0.0:
                    monthly_tds = min(monthly_tds, remaining_tax)
            else:
                # Fallback: spread remaining annual tax over remaining payroll months
                if remaining_months <= 0:
                    monthly_tds = 0.0
                elif remaining_months == 1:
                    monthly_tds = round(remaining_tax, 2)
                else:
                    monthly_tds = round(remaining_tax / remaining_months, 2)

            slip.tds_engine_tds_id = tds
            slip.tds_engine_projected_income = max(
                (tds.income_chargeable_salaries or 0.0) + (tds.total_other_income or 0.0),
                0.0,
            )
            slip.tds_engine_annual_tax = annual_tax
            slip.tds_engine_tds_deducted_till_date = deducted_till_date
            slip.tds_engine_remaining_tax = remaining_tax
            slip.tds_engine_remaining_months = remaining_months
            slip.tds_engine_monthly_tds = max(monthly_tds, 0.0)

    def _get_pdf_reports(self):
        """Override to use our custom KPT format report instead of missing hr_payroll report"""
        # Try to get the KPT format report, fallback to standard report if not found
        try:
            kpt_report = self.env.ref('hr_contract_extension.report_salary_slip_kpt_format', raise_if_not_found=False)
            if kpt_report:
                classic_report = kpt_report
            else:
                # Fallback to standard report
                classic_report = self.env.ref('hr_contract_extension.report_salary_slip', raise_if_not_found=False)
                if not classic_report:
                    # Last resort: try to find any payslip report
                    classic_report = self.env['ir.actions.report'].search([
                        ('model', '=', 'hr.payslip'),
                        ('report_type', '=', 'qweb-pdf')
                    ], limit=1)
        except Exception:
            # If all else fails, try to get any payslip report
            classic_report = self.env['ir.actions.report'].search([
                ('model', '=', 'hr.payslip'),
                ('report_type', '=', 'qweb-pdf')
            ], limit=1)
        
        if not classic_report:
            # Create a minimal report reference to avoid errors
            return {}
        
        result = defaultdict(lambda: self.env['hr.payslip'])
        for payslip in self:
            if not payslip.struct_id or not payslip.struct_id.report_id:
                result[classic_report] |= payslip
            else:
                result[payslip.struct_id.report_id] |= payslip
        return result

    def _number_to_words_indian(self, amount):
        """Convert number to Indian words format (e.g., 886364 -> 'Eight Lakh Eighty-Six Thousand Three Hundred Sixty-Four')"""
        def convert_to_words(num):
            ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten',
                   'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
            tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
            
            if num == 0:
                return ''
            elif num < 20:
                return ones[num]
            elif num < 100:
                return tens[num // 10] + ('-' + ones[num % 10] if num % 10 else '')
            elif num < 1000:
                return ones[num // 100] + ' Hundred' + (' ' + convert_to_words(num % 100) if num % 100 else '')
            elif num < 100000:
                return convert_to_words(num // 1000) + ' Thousand' + (' ' + convert_to_words(num % 1000) if num % 1000 else '')
            elif num < 10000000:
                return convert_to_words(num // 100000) + ' Lakh' + (' ' + convert_to_words(num % 100000) if num % 100000 else '')
            else:
                return convert_to_words(num // 10000000) + ' Crore' + (' ' + convert_to_words(num % 10000000) if num % 10000000 else '')
        
        # Handle decimal part
        amount = float(amount)
        rupees = int(amount)
        paise = int(round((amount - rupees) * 100))
        
        words = convert_to_words(rupees)
        if words:
            words += ' Rupees'
        else:
            words = 'Zero Rupees'
        
        if paise > 0:
            words += ' and ' + convert_to_words(paise) + ' Paise'
        
        words += ' Only'
        return words
