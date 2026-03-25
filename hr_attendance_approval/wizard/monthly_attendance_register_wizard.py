# -*- coding: utf-8 -*-

import base64
import io
from calendar import monthrange
from datetime import date, datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class MonthlyAttendanceRegisterWizard(models.TransientModel):
    _name = 'hr.monthly.attendance.register.wizard'
    _description = 'Monthly Attendance Register (XLSX)'

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
    year = fields.Char(string='Year', required=True, default=lambda self: str(datetime.now().year))

    department_ids = fields.Many2many('hr.department', string='Units (Departments)')
    employee_ids = fields.Many2many('hr.employee', string='Employees')

    scope = fields.Selection(
        [
            ('my', 'My (Employee)'),
            ('my_team', 'My Team (Manager)'),
            ('all', 'All (HR)'),
        ],
        string='Scope',
        required=True,
        default='my',
    )

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    output_file = fields.Binary('Attendance Register', readonly=True)
    output_file_name = fields.Char('File Name', readonly=True)
    state = fields.Selection([('draft', 'Configure'), ('done', 'Done')], default='draft')

    def _scope_domain(self):
        self.ensure_one()

        if self.scope == 'my':
            return [('user_id', '=', self.env.user.id)]

        if self.scope == 'my_team':
            if not self.env.user.has_group('hr_attendance_approval.group_attendance_approval_manager'):
                raise UserError(_('You are not allowed to generate the report for your team.'))
            return [('parent_id.user_id', '=', self.env.user.id)]

        if self.scope == 'all':
            if not self.env.user.has_group('hr_attendance_approval.group_attendance_approval_admin'):
                raise UserError(_('You are not allowed to generate the report for all employees.'))
            return []

        return [('id', '=', 0)]

    def _get_period(self):
        self.ensure_one()
        try:
            y = int(self.year)
            m = int(self.month)
        except Exception:
            raise UserError(_('Invalid month/year.'))

        last_day = monthrange(y, m)[1]
        date_from = date(y, m, 1)
        date_to = date(y, m, last_day)
        return date_from, date_to

    def _get_employees(self):
        self.ensure_one()
        domain = [('company_id', '=', self.company_id.id)] + self._scope_domain()

        if self.employee_ids:
            domain.append(('id', 'in', self.employee_ids.ids))

        if self.department_ids:
            domain.append(('department_id', 'in', self.department_ids.ids))

        return self.env['hr.employee'].search(domain, order='department_id, name')

    def _get_public_holiday_dates(self, employee, date_from, date_to):
        """Return a set of dates that are public holidays for the employee calendar.

        Implementation note:
        - Odoo stores calendar time off in resource.calendar.leaves.
        - We treat leaves with a linked calendar as "holiday" for the register.
        """
        cal = employee.resource_calendar_id
        if not cal:
            cal = self.env.company.resource_calendar_id

        if not cal:
            return set()

        leaves = self.env['resource.calendar.leaves'].search([
            ('calendar_id', '=', cal.id),
            ('date_from', '<=', datetime.combine(date_to, datetime.max.time())),
            ('date_to', '>=', datetime.combine(date_from, datetime.min.time())),
        ])

        days = set()
        for leave in leaves:
            start_dt = fields.Datetime.to_datetime(leave.date_from)
            end_dt = fields.Datetime.to_datetime(leave.date_to)
            if not start_dt or not end_dt:
                continue

            cur = start_dt.date()
            end = end_dt.date()
            while cur <= end:
                if date_from <= cur <= date_to:
                    days.add(cur)
                cur += timedelta(days=1)

        return days

    def _get_attendances_by_employee_day(self, employees, date_from, date_to):
        """Return dict emp_id -> dict day -> {'present': bool, 'overtime': float}.

        We consider an employee "present" if they have at least one attendance with
        a check_in on that day.
        """
        if not employees:
            return {}

        dt_from = datetime.combine(date_from, datetime.min.time())
        dt_to = datetime.combine(date_to, datetime.max.time())

        # Only count attendances that are fully approved.
        # We rely on the approval object as the source of truth.
        approved_attendance_ids = set(self.env['hr.attendance.approval'].search([
            ('employee_id', 'in', employees.ids),
            ('attendance_date', '>=', date_from),
            ('attendance_date', '<=', date_to),
            ('state', '=', 'approved'),
            ('hr_attendance_id', '!=', False),
        ]).mapped('hr_attendance_id').ids)

        attendances = self.env['hr.attendance'].search([
            ('employee_id', 'in', employees.ids),
            ('check_in', '>=', dt_from),
            ('check_in', '<=', dt_to),
        ])

        if approved_attendance_ids:
            attendances = attendances.filtered(lambda a: a.id in approved_attendance_ids)
        else:
            attendances = self.env['hr.attendance']

        out = {emp.id: {} for emp in employees}
        for att in attendances:
            day = fields.Datetime.to_datetime(att.check_in).date() if att.check_in else False
            if not day:
                continue
            emp_map = out.setdefault(att.employee_id.id, {})
            day_map = emp_map.setdefault(day, {'present': False, 'overtime': 0.0})
            day_map['present'] = True
            day_map['overtime'] += float(att.overtime_hours or 0.0)

        return out

    def action_generate(self):
        self.ensure_one()

        if not xlsxwriter:
            raise UserError(_('Required Python library (xlsxwriter) is not installed. Please install it: pip install xlsxwriter'))

        date_from, date_to = self._get_period()
        employees = self._get_employees()
        if not employees:
            raise UserError(_('No employees found matching the selected criteria.'))

        attendance_map = self._get_attendances_by_employee_day(employees, date_from, date_to)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Attendance Register')

        title_format = workbook.add_format({'bold': True, 'align': 'center', 'font_size': 12})
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'border': 1, 'bg_color': '#D9E1F2'})
        data_format = workbook.add_format({'align': 'left', 'border': 1})
        num_format = workbook.add_format({'align': 'center', 'border': 1})
        unit_format = workbook.add_format({'bold': True, 'align': 'left', 'border': 1, 'bg_color': '#F2F2F2'})

        month_name = dict(self._fields['month'].selection).get(self.month, '')
        worksheet.merge_range(0, 0, 0, 8, f'KPT Piping System Pvt Ltd', title_format)
        worksheet.merge_range(1, 0, 1, 8, f'Salary/Manager for the month of {month_name}, {self.year}', title_format)

        headers = ['S.No', 'Name', 'Total Days', 'Absent', 'Present', 'Overtime', 'Holiday', 'Total Present']
        for col, head in enumerate(headers):
            worksheet.write(3, col, head, header_format)

        worksheet.set_column(0, 0, 6)
        worksheet.set_column(1, 1, 35)
        worksheet.set_column(2, 7, 14)

        row = 4
        serial = 1

        def _dept_sort_key(emp):
            return ((emp.department_id.name or '').lower() if emp.department_id else 'zzz', (emp.name or '').lower())

        employees_sorted = employees.sorted(key=_dept_sort_key)
        current_dept = False

        total_days_in_month = (date_to - date_from).days + 1

        for emp in employees_sorted:
            dept = emp.department_id
            if dept != current_dept:
                current_dept = dept
                unit_label = dept.name if dept else 'No Unit'
                worksheet.merge_range(row, 0, row, 7, f'Unit : {unit_label}', unit_format)
                row += 1

            holidays = self._get_public_holiday_dates(emp, date_from, date_to)
            present_days = 0
            overtime_hours = 0.0

            day_map = attendance_map.get(emp.id, {})
            for d in (date_from + timedelta(days=i) for i in range(total_days_in_month)):
                if d in holidays:
                    continue
                vals = day_map.get(d)
                if vals and vals.get('present'):
                    present_days += 1
                    overtime_hours += float(vals.get('overtime') or 0.0)

            holiday_days = len(holidays)
            absent_days = max(total_days_in_month - present_days - holiday_days, 0)
            total_present = present_days + holiday_days

            worksheet.write(row, 0, serial, num_format)
            worksheet.write(row, 1, emp.name or '', data_format)
            worksheet.write(row, 2, total_days_in_month, num_format)
            worksheet.write(row, 3, absent_days, num_format)
            worksheet.write(row, 4, present_days, num_format)
            worksheet.write(row, 5, round(overtime_hours, 2), num_format)
            worksheet.write(row, 6, holiday_days, num_format)
            worksheet.write(row, 7, total_present, num_format)

            row += 1
            serial += 1

        workbook.close()
        output.seek(0)

        filename = f'Attendance_Register_{month_name}_{self.year}.xlsx'
        output_b64 = base64.b64encode(output.getvalue())

        self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': output_b64,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        self.write({
            'output_file': output_b64,
            'output_file_name': filename,
            'state': 'done',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context,
        }

    def action_download(self):
        self.ensure_one()
        if not self.output_file:
            raise UserError(_('No report available. Please generate it first.'))
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model={self._name}&id={self.id}&field=output_file&download=true&filename={self.output_file_name}',
            'target': 'self',
        }

    def action_new(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }
