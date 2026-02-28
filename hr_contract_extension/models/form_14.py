# -*- coding: utf-8 -*-

from calendar import monthrange
from datetime import date, datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrContractForm14(models.Model):
    _name = 'hr.contract.form14'
    _description = 'Form 14 - Leave with Wages Register'
    _order = 'year desc, month desc, employee_id'

    name = fields.Char(string='Reference', readonly=True, copy=False)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)

    contract_id = fields.Many2one('hr.contract', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', related='contract_id.employee_id', store=True, readonly=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True, readonly=True)

    month = fields.Selection(
        [
            ('01', 'January'), ('02', 'February'), ('03', 'March'),
            ('04', 'April'), ('05', 'May'), ('06', 'June'),
            ('07', 'July'), ('08', 'August'), ('09', 'September'),
            ('10', 'October'), ('11', 'November'), ('12', 'December'),
        ],
        string='Month',
        required=True,
        default=lambda self: fields.Date.context_today(self).strftime('%m'),
    )
    year = fields.Integer(string='Year', required=True, default=lambda self: fields.Date.context_today(self).year)

    wages_period_from = fields.Date(string='Wages Period From')
    wages_period_to = fields.Date(string='Wages Period To')

    # Header fields on the printed form
    serial_no = fields.Integer(string='Sl. No.')
    register_adult_child_no = fields.Char(string='Sl. No. in Register of Adult/Child')
    name_of_factory = fields.Char(string='Name of Factory')
    father_name = fields.Char(string="Father's Name")
    date_of_entry_into_service = fields.Date(string='Date of Entry into Service')
    date_of_discharge = fields.Date(string='Date of Discharge')
    payment_in_lieu_date = fields.Date(string='Date of Payment made in lieu of leave due')
    payment_in_lieu_amount = fields.Float(string='Amount of Payment made in lieu of leave due')

    # --- Register columns (as per the printed Form 14 numbering) ---
    col_01_calendar_year_of_service = fields.Char(string='1. Calendar year of Service')
    col_04_days_worked = fields.Integer(string='4. No. of days worked during the year')
    col_05_days_layoff = fields.Integer(string='5. No. of days of lay off')
    col_06_days_maternity_leave = fields.Integer(string='6. No. of days of maternity leave')
    col_07_days_leave_earned_for_work = fields.Integer(string='7. No. of days leave earned')
    col_08_total_4_to_7 = fields.Integer(string='8. Total of Cols 4-7', compute='_compute_totals', store=True)

    col_09_leave_balance_prev_year = fields.Integer(string='9. Balance of leave at credit at end of previous year')
    col_10_leave_earned_during_year = fields.Integer(string='10. Leave earned during the year')
    col_11_total_9_10 = fields.Integer(string='11. Total of Cols 9-10', compute='_compute_totals', store=True)

    col_12_scheme_79_8_accepted = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        string='12. Whether leave under sec 79(8) was accepted',
    )

    col_13_leave_enjoyed_from = fields.Date(string='13. Leave enjoyed - From')
    col_14_leave_enjoyed_to = fields.Date(string='14. Leave enjoyed - To')
    col_15_leave_balance_after = fields.Integer(string='15. Balance of leave at credit')

    col_16_normal_rate_of_wages = fields.Float(string='16. Normal rate of wages')
    col_17_cash_equivalent_at_discharge = fields.Float(string='17. Cash equivalent of leave at credit at time of discharge')

    col_18_sick = fields.Integer(string='18. Sick')
    col_19_without_pay = fields.Integer(string='19. Without pay')
    col_20_absent = fields.Integer(string='20. Absent')

    col_21_remarks = fields.Char(string='21. Remarks')
    col_22_extra = fields.Char(string='22. Extra')

    state = fields.Selection([
        ('generated', 'Generated'),
        ('locked', 'Locked'),
    ], default='generated', required=True)

    _sql_constraints = [
        ('uniq_form14_contract_month', 'unique(contract_id, year, month)', 'Form 14 already exists for this contract/month.'),
    ]

    @api.depends(
        'col_04_days_worked',
        'col_05_days_layoff',
        'col_06_days_maternity_leave',
        'col_07_days_leave_earned_for_work',
        'col_09_leave_balance_prev_year',
        'col_10_leave_earned_during_year',
    )
    def _compute_totals(self):
        for rec in self:
            rec.col_08_total_4_to_7 = (
                (rec.col_04_days_worked or 0)
                + (rec.col_05_days_layoff or 0)
                + (rec.col_06_days_maternity_leave or 0)
                + (rec.col_07_days_leave_earned_for_work or 0)
            )
            rec.col_11_total_9_10 = (rec.col_09_leave_balance_prev_year or 0) + (rec.col_10_leave_earned_during_year or 0)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if not rec.name:
                rec.name = rec._compute_reference()
        return records

    def write(self, vals):
        # Allow edits even after generation; only block if explicitly locked.
        locked = self.filtered(lambda r: r.state == 'locked')
        if locked and any(k not in ('state',) for k in vals.keys()):
            raise UserError(_('This Form 14 record is locked.'))
        return super().write(vals)

    def _compute_reference(self):
        self.ensure_one()
        month_name = dict(self._fields['month'].selection).get(self.month, self.month)
        emp = self.employee_id.name or ''
        return f'Form 14 - {emp} - {month_name} {self.year}'

    def action_print(self):
        self.ensure_one()
        return self.env.ref('hr_contract_extension.action_report_hr_contract_form14_register').report_action(self)

    @api.model
    def _default_factory_name(self, contract):
        return (contract.company_id.name if contract.company_id else False) or False

    @api.model
    def _default_entry_date(self, contract):
        return contract.date_start or (contract.employee_id.contract_id.date_start if contract.employee_id and contract.employee_id.contract_id else False)

    @api.model
    def _prepare_month_defaults(self, contract, year, month):
        last_day = monthrange(year, int(month))[1]
        dt_from = date(year, int(month), 1)
        dt_to = date(year, int(month), last_day)

        dt_from_dt = datetime.combine(dt_from, datetime.min.time())
        dt_to_dt = datetime.combine(dt_to, datetime.max.time())
        attendances = self.env['hr.attendance'].search([
            ('employee_id', '=', contract.employee_id.id),
            ('check_in', '>=', fields.Datetime.to_datetime(dt_from_dt)),
            ('check_in', '<=', fields.Datetime.to_datetime(dt_to_dt)),
        ])
        worked_days = len(set(fields.Datetime.to_datetime(a.check_in).date() for a in attendances if a.check_in))
        leave_earned = int((worked_days or 0) // 20)

        prev_year = year
        prev_month = int(month) - 1
        if prev_month <= 0:
            prev_month = 12
            prev_year = year - 1

        prev = self.search([
            ('contract_id', '=', contract.id),
            ('year', '=', prev_year),
            ('month', '=', str(prev_month).zfill(2)),
        ], limit=1)

        prev_balance = prev.col_15_leave_balance_after if prev else 0
        leave_balance = max(int(prev_balance or 0) + int(leave_earned or 0), 0)

        return {
            'wages_period_from': dt_from,
            'wages_period_to': dt_to,
            'name_of_factory': self._default_factory_name(contract),
            'father_name': getattr(contract.employee_id, 'father_name', False) or getattr(contract.employee_id, 'father_husband_name', False) or False,
            'date_of_entry_into_service': self._default_entry_date(contract),
            'col_01_calendar_year_of_service': str(year),
            'col_04_days_worked': worked_days,
            'col_07_days_leave_earned_for_work': leave_earned,
            'col_09_leave_balance_prev_year': int(prev_balance or 0),
            'col_10_leave_earned_during_year': int(leave_earned or 0),
            'col_12_scheme_79_8_accepted': 'yes',
            'col_15_leave_balance_after': leave_balance,
            'col_16_normal_rate_of_wages': float(contract.wage or 0.0),
        }

    @api.model
    def _cron_generate_monthly_form14(self):
        today = fields.Date.context_today(self)
        last_day = monthrange(today.year, today.month)[1]
        if today.day != last_day:
            return

        month = str(today.month).zfill(2)
        year = today.year

        contracts = self.env['hr.contract'].search([
            ('state', '=', 'open'),
            ('active', '=', True),
        ])

        for contract in contracts:
            existing = self.search([
                ('contract_id', '=', contract.id),
                ('year', '=', year),
                ('month', '=', month),
            ], limit=1)
            if existing:
                continue

            vals = {
                'company_id': contract.company_id.id,
                'contract_id': contract.id,
                'year': year,
                'month': month,
            }
            vals.update(self._prepare_month_defaults(contract, year, month))
            self.create(vals)


class HrContract(models.Model):
    _inherit = 'hr.contract'

    form14_ids = fields.One2many('hr.contract.form14', 'contract_id', string='Form 14 Records')
    form14_count = fields.Integer(string='Form 14 Count', compute='_compute_form14_count')

    def _compute_form14_count(self):
        for rec in self:
            rec.form14_count = len(rec.form14_ids)

    def action_open_form14(self):
        self.ensure_one()
        return {
            'name': _('Form 14'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.contract.form14',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('contract_id', '=', self.id)],
            'context': {
                **self.env.context,
                'default_contract_id': self.id,
                'default_company_id': self.company_id.id,
            },
        }
