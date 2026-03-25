# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from odoo import http
from odoo.http import request


class AttendanceDashboardController(http.Controller):

    @http.route('/attendance/dashboard', type='http', auth='user', website=False)
    def dashboard(self, **kwargs):
        """Render the attendance dashboard page."""
        return request.render('bulk_attendance_upload.attendance_dashboard_template', {
            'user': request.env.user,
        })

    def _get_allowed_employee_ids(self):
        """Get list of employee IDs the current user is allowed to see.
        For managers with team access, returns their subordinates. For others, returns None (all employees).
        """
        user = request.env.user
        if hasattr(user, '_get_restricted_employee_ids'):
            allowed_ids = user._get_restricted_employee_ids()
            return allowed_ids  # Can be None (no restriction), [] (no access), or list of IDs
        return None  # No restriction

    @http.route('/attendance/dashboard/data', type='http', auth='user', methods=['GET', 'POST'], csrf=False)
    def dashboard_data(self, **kwargs):
        """Return JSON data for dashboard cards and charts."""
        today = datetime.now().date()
        # Period (for daily chart) from query param, default 7 days, max 30
        try:
            period = int(request.params.get('period', 7))
        except (TypeError, ValueError):
            period = 7
        period = max(1, min(period, 30))

        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # Get attendance records
        Attendance = request.env['hr.attendance']
        
        # Get allowed employee IDs for filtering
        allowed_employee_ids = self._get_allowed_employee_ids()
        employee_domain = [('active', '=', True)]
        attendance_domain = []
        
        if allowed_employee_ids is not None:
            if not allowed_employee_ids:
                # User has no access to any employees
                employee_domain.append(('id', '=', False))
                attendance_domain.append(('employee_id', '=', False))
            else:
                # Filter by allowed employees
                employee_domain.append(('id', 'in', allowed_employee_ids))
                attendance_domain.append(('employee_id', 'in', allowed_employee_ids))
        
        # Total employees
        total_employees = request.env['hr.employee'].search_count(employee_domain)

        # Today's check-ins
        today_domain = [
            ('check_in', '>=', datetime.combine(today, datetime.min.time())),
            ('check_in', '<', datetime.combine(today + timedelta(days=1), datetime.min.time()))
        ]
        if attendance_domain:
            today_domain = attendance_domain + today_domain
        today_checkins = Attendance.search_count(today_domain)

        # Employees currently at work
        at_work_domain = [('check_out', '=', False)]
        if attendance_domain:
            at_work_domain = attendance_domain + at_work_domain
        at_work = Attendance.search_count(at_work_domain)

        # This week's total hours
        week_domain = [
            ('check_in', '>=', datetime.combine(week_ago, datetime.min.time())),
            ('check_in', '<', datetime.combine(today + timedelta(days=1), datetime.min.time())),
            ('check_out', '!=', False)
        ]
        if attendance_domain:
            week_domain = attendance_domain + week_domain
        week_attendances = Attendance.search(week_domain)
        week_total_hours = sum(week_attendances.mapped('worked_hours')) or 0

        # This month's total hours
        month_domain = [
            ('check_in', '>=', datetime.combine(month_ago, datetime.min.time())),
            ('check_in', '<', datetime.combine(today + timedelta(days=1), datetime.min.time())),
            ('check_out', '!=', False)
        ]
        if attendance_domain:
            month_domain = attendance_domain + month_domain
        month_attendances = Attendance.search(month_domain)
        month_total_hours = sum(month_attendances.mapped('worked_hours')) or 0

        # Overtime this month
        month_overtime = sum(month_attendances.mapped('overtime_hours')) or 0

        # Daily attendance for last N days (for chart)
        daily_data = []
        for i in range(period - 1, -1, -1):
            day = today - timedelta(days=i)
            day_start = datetime.combine(day, datetime.min.time())
            day_end = datetime.combine(day + timedelta(days=1), datetime.min.time())
            day_domain = [
                ('check_in', '>=', day_start),
                ('check_in', '<', day_end),
                ('check_out', '!=', False)
            ]
            if attendance_domain:
                day_domain = attendance_domain + day_domain
            day_attendances = Attendance.search(day_domain)
            day_hours = sum(day_attendances.mapped('worked_hours')) or 0
            daily_data.append({
                'date': day.strftime('%Y-%m-%d'),
                'label': day.strftime('%a %d'),
                'hours': round(day_hours, 2)
            })

        # Top employees by hours this week
        employee_hours = {}
        for att in week_attendances:
            emp_id = att.employee_id.id
            if emp_id not in employee_hours:
                employee_hours[emp_id] = {
                    'name': att.employee_id.name,
                    'hours': 0
                }
            employee_hours[emp_id]['hours'] += att.worked_hours or 0

        top_employees = sorted(
            list(employee_hours.values()),
            key=lambda x: x['hours'],
            reverse=True
        )[:5]

        import json
        data = {
            'cards': {
                'total_employees': total_employees,
                'today_checkins': today_checkins,
                'at_work': at_work,
                'week_hours': round(week_total_hours, 2),
                'month_hours': round(month_total_hours, 2),
                'month_overtime': round(month_overtime, 2),
            },
            'daily_chart': daily_data,
            'top_employees': top_employees,
        }
        return request.make_response(
            json.dumps(data),
            headers=[('Content-Type', 'application/json')]
        )
