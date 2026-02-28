# -*- coding: utf-8 -*-

import pytz
from calendar import monthrange
from datetime import date, datetime, time, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MonthlyAttendanceSetWizard(models.TransientModel):
    _name = 'monthly.attendance.set.wizard'
    _description = 'Set Month Attendance at Once'
    _order = 'year desc, month desc, employee_id'

    @api.model
    def _get_employee_domain(self):
        """Get domain for employee field based on manager restrictions."""
        domain = [('active', '=', True)]
        if hasattr(self.env.user, '_get_restricted_employee_ids'):
            allowed_ids = self.env.user._get_restricted_employee_ids()
            if allowed_ids is not None:
                if not allowed_ids:
                    domain.append(('id', '=', False))  # No access
                else:
                    domain.append(('id', 'in', allowed_ids))
        return domain

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        domain=lambda self: self._get_employee_domain(),
        help='Employee for whom to create the month attendance.',
    )
    month = fields.Selection(
        [
            ('01', 'January'), ('02', 'February'), ('03', 'March'),
            ('04', 'April'), ('05', 'May'), ('06', 'June'),
            ('07', 'July'), ('08', 'August'), ('09', 'September'),
            ('10', 'October'), ('11', 'November'), ('12', 'December'),
        ],
        string='Month',
        required=True,
        default=lambda self: str(datetime.now().month).zfill(2),
    )
    year = fields.Char(
        string='Year',
        required=True,
        default=lambda self: str(datetime.now().year),
    )
    total_present_days = fields.Integer(
        string='Total Present Days',
        required=True,
        default=0,
        help='Number of working days to mark as present. Attendance will be created only on working days (excluding Sundays and holidays).',
    )
    total_overtime_hours = fields.Float(
        string='Total Overtime (Hours)',
        default=0.0,
        help='Total overtime hours for the month. Will be distributed evenly across the present days.',
    )
    default_check_in = fields.Float(
        string='Default Check In',
        default=9.0,
        help='Time in hours (e.g. 9.0 = 09:00 AM).',
    )
    default_check_out = fields.Float(
        string='Default Check Out',
        default=18.0,
        help='Time in hours (e.g. 18.0 = 06:00 PM). Base working day length is used; overtime is added on top.',
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Created'),
    ], string='Status', default='draft', readonly=True)
    
    month_display = fields.Char(
        string='Month Name',
        compute='_compute_month_display',
        store=False,
        help='Display name for month grouping'
    )
    
    @api.depends('month')
    def _compute_month_display(self):
        month_map = {
            '01': 'January', '02': 'February', '03': 'March',
            '04': 'April', '05': 'May', '06': 'June',
            '07': 'July', '08': 'August', '09': 'September',
            '10': 'October', '11': 'November', '12': 'December',
        }
        for record in self:
            record.month_display = month_map.get(record.month, record.month)

    def _get_working_weekdays(self, calendar):
        """Return set of Python weekday integers (0=Monday, 6=Sunday) that are working days in the calendar."""
        if not calendar or not calendar.attendance_ids:
            # Default: Monday–Friday
            return {0, 1, 2, 3, 4}
        return {int(a.dayofweek) for a in calendar.attendance_ids}

    def _get_holiday_dates(self, calendar, date_from, date_to):
        """Return set of dates that are holidays (resource.calendar.leaves) for the given calendar in the period."""
        if not calendar:
            return set()
        leaves = self.env['resource.calendar.leaves'].search([
            ('calendar_id', '=', calendar.id),
            ('date_from', '<=', datetime.combine(date_to, datetime.max.time())),
            ('date_to', '>=', datetime.combine(date_from, datetime.min.time())),
        ])
        holiday_dates = set()
        for leave in leaves:
            start_dt = fields.Datetime.to_datetime(leave.date_from)
            end_dt = fields.Datetime.to_datetime(leave.date_to)
            if not start_dt or not end_dt:
                continue
            cur = start_dt.date()
            end = end_dt.date()
            while cur <= end:
                if date_from <= cur <= date_to:
                    holiday_dates.add(cur)
                cur += timedelta(days=1)
        return holiday_dates

    def _get_working_days_in_month(self):
        """
        Return a sorted list of dates in the selected month that are working days
        (according to employee's resource calendar) and not holidays.
        """
        self.ensure_one()
        try:
            y = int(self.year)
            m = int(self.month)
        except (ValueError, TypeError):
            raise UserError(_('Invalid month or year.'))

        last_day = monthrange(y, m)[1]
        date_from = date(y, m, 1)
        date_to = date(y, m, last_day)

        employee = self.employee_id
        calendar = employee.resource_calendar_id or employee.company_id.resource_calendar_id
        working_weekdays = self._get_working_weekdays(calendar)
        holidays = self._get_holiday_dates(calendar, date_from, date_to)

        working_days = []
        d = date_from
        while d <= date_to:
            # Python: Monday=0, Sunday=6
            if d.weekday() in working_weekdays and d not in holidays:
                working_days.append(d)
            d += timedelta(days=1)
        return sorted(working_days)

    def _float_to_time(self, float_val):
        """Convert float hour to time object."""
        h = int(float_val)
        m = int((float_val - h) * 60)
        return time(h, min(m, 59), 0)

    def _localize_dt(self, dt):
        """Convert naive datetime to UTC based on user's timezone."""
        user_tz = self.env.user.tz or 'UTC'
        local = pytz.timezone(user_tz)
        local_dt = local.localize(dt, is_dst=None)
        return local_dt.astimezone(pytz.UTC).replace(tzinfo=None)

    def action_create_attendance(self):
        """Create attendance records for the selected employee and month."""
        self.ensure_one()
        # Check if user is allowed to create attendance for this employee
        if hasattr(self.env.user, '_get_restricted_employee_ids'):
            allowed_ids = self.env.user._get_restricted_employee_ids()
            if allowed_ids is not None and self.employee_id.id not in allowed_ids:
                raise UserError(_('You are not authorized to create attendance for employee %s.') % self.employee_id.name)
        
        if self.total_present_days <= 0:
            raise UserError(_('Total Present Days must be greater than 0.'))

        working_days = self._get_working_days_in_month()
        if not working_days:
            raise UserError(_(
                'There are no working days in the selected month for this employee '
                '(all days are weekend or holiday according to the calendar).'
            ))

        # How many present days we can fill
        n_days = min(self.total_present_days, len(working_days))
        days_to_mark = working_days[:n_days]

        overtime_per_day = (self.total_overtime_hours or 0.0) / n_days if n_days else 0.0
        base_hours = (self.default_check_out or 18.0) - (self.default_check_in or 9.0)
        if base_hours <= 0:
            base_hours = 8.0
        hours_per_day = base_hours + overtime_per_day

        t_in = self._float_to_time(self.default_check_in)
        created = 0
        employee = self.employee_id
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')

        for d in days_to_mark:
            # Already have attendance on this day? Skip (do not duplicate).
            local_start = user_tz.localize(datetime.combine(d, time.min))
            local_end = user_tz.localize(datetime.combine(d, time.max))
            utc_start = local_start.astimezone(pytz.UTC).replace(tzinfo=None)
            utc_end = local_end.astimezone(pytz.UTC).replace(tzinfo=None)
            exists = self.env['hr.attendance'].search_count([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', utc_start),
                ('check_in', '<=', utc_end),
            ])
            if exists:
                continue

            dt_in = datetime.combine(d, t_in)
            dt_out = dt_in + timedelta(hours=hours_per_day)
            utc_in = self._localize_dt(dt_in)
            utc_out = self._localize_dt(dt_out)

            self.env['hr.attendance'].create({
                'employee_id': employee.id,
                'check_in': utc_in,
                'check_out': utc_out,
            })
            created += 1

        message = _(
            'Created %(count)s attendance record(s) for %(employee)s in %(month)s/%(year)s. '
            'Working days in month: %(total)s (Sundays and holidays excluded).'
        ) % {
            'count': created,
            'employee': employee.name,
            'month': self.month,
            'year': self.year,
            'total': len(working_days),
        }
        if self.total_present_days > len(working_days):
            message += ' ' + _(
                'You requested %s present days but only %s working days exist; only those were used.'
            ) % (self.total_present_days, len(working_days))

        self.write({'state': 'done'})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': message,
                'type': 'success',
                'sticky': True,
            },
        }
    
    def action_create_attendance_batch(self):
        """Batch action to create attendance for multiple records"""
        records = self.filtered(lambda r: r.state == 'draft')
        if not records:
            raise UserError(_('No draft records selected.'))
        for record in records:
            record.action_create_attendance()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Created attendance for %s record(s).') % len(records),
                'type': 'success',
                'sticky': True,
            },
        }
