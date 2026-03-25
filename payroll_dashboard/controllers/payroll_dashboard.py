# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from calendar import monthrange
from odoo import http
from odoo.http import request
import json


class PayrollDashboardController(http.Controller):

    @http.route('/payroll/dashboard', type='http', auth='user', website=False)
    def dashboard(self, **kwargs):
        """Render the payroll dashboard page."""
        return request.render('payroll_dashboard.payroll_dashboard_template', {
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

    @http.route('/payroll/dashboard/data', type='http', auth='user', methods=['GET', 'POST'], csrf=False)
    def dashboard_data(self, **kwargs):
        """Return JSON data for dashboard cards and charts."""
        today = datetime.now().date()
        
        # Period (for monthly chart) from query param, default 6 months, max 12
        try:
            period = int(request.params.get('period', 6))
        except (TypeError, ValueError):
            period = 6
        period = max(1, min(period, 12))

        # Get current month start and end
        current_month_start = today.replace(day=1)
        current_month_end = today.replace(day=monthrange(today.year, today.month)[1])
        
        # Get last month
        if today.month == 1:
            last_month_start = datetime(today.year - 1, 12, 1).date()
            last_month_end = datetime(today.year - 1, 12, monthrange(today.year - 1, 12)[1]).date()
        else:
            last_month_start = today.replace(month=today.month - 1, day=1)
            last_month_end = today.replace(month=today.month - 1, day=monthrange(today.year, today.month - 1)[1])

        # Get allowed employee IDs for filtering
        allowed_employee_ids = self._get_allowed_employee_ids()
        employee_domain = [('active', '=', True)]
        payslip_domain = []
        contract_domain = [('state', '=', 'open')]
        
        if allowed_employee_ids is not None:
            if not allowed_employee_ids:
                # User has no access to any employees
                employee_domain.append(('id', '=', False))
                payslip_domain.append(('employee_id', '=', False))
                contract_domain.append(('employee_id', '=', False))
            else:
                # Filter by allowed employees
                employee_domain.append(('id', 'in', allowed_employee_ids))
                payslip_domain.append(('employee_id', 'in', allowed_employee_ids))
                contract_domain.append(('employee_id', 'in', allowed_employee_ids))
        
        # Total employees
        total_employees = request.env['hr.employee'].search_count(employee_domain)

        # Active contracts
        active_contracts = request.env['hr.contract'].search_count(contract_domain)

        # Payslips generated this month
        current_month_payslip_domain = payslip_domain + [
            ('date_from', '>=', current_month_start),
            ('date_from', '<=', current_month_end)
        ]
        payslips_this_month = request.env['hr.payslip'].search_count(current_month_payslip_domain)

        # Total payroll amount this month
        payslips_current = request.env['hr.payslip'].search(
            current_month_payslip_domain + [('state', '=', 'done')]
        )
        total_payroll_current = sum(payslips_current.mapped('net_wage')) or 0.0

        # Total payroll amount last month
        last_month_payslip_domain = payslip_domain + [
            ('date_from', '>=', last_month_start),
            ('date_from', '<=', last_month_end),
            ('state', '=', 'done')
        ]
        payslips_last = request.env['hr.payslip'].search(last_month_payslip_domain)
        total_payroll_last = sum(payslips_last.mapped('net_wage')) or 0.0

        # Pending payslips (draft state)
        pending_payslips = request.env['hr.payslip'].search_count(
            payslip_domain + [('state', '=', 'draft')]
        )

        # Average salary (from active contracts)
        active_contracts_records = request.env['hr.contract'].search(contract_domain)
        if active_contracts_records:
            avg_salary = sum(active_contracts_records.mapped('wage')) / len(active_contracts_records)
        else:
            avg_salary = 0.0

        # Monthly payroll trend for last N months (for chart)
        monthly_data = []
        for i in range(period - 1, -1, -1):
            # Calculate month start and end
            if today.month - i <= 0:
                month = today.month - i + 12
                year = today.year - 1
            else:
                month = today.month - i
                year = today.year
            
            month_start = datetime(year, month, 1).date()
            month_end = datetime(year, month, monthrange(year, month)[1]).date()
            
            month_domain = payslip_domain + [
                ('date_from', '>=', month_start),
                ('date_from', '<=', month_end),
                ('state', '=', 'done')
            ]
            month_payslips = request.env['hr.payslip'].search(month_domain)
            month_total = sum(month_payslips.mapped('net_wage')) or 0.0
            
            monthly_data.append({
                'month': month_start.strftime('%Y-%m'),
                'label': month_start.strftime('%b %Y'),
                'amount': round(month_total, 2)
            })

        # Top earners (by net wage in current month)
        employee_salaries = {}
        for payslip in payslips_current:
            emp_id = payslip.employee_id.id
            if emp_id not in employee_salaries:
                employee_salaries[emp_id] = {
                    'name': payslip.employee_id.name,
                    'amount': 0.0
                }
            employee_salaries[emp_id]['amount'] += payslip.net_wage or 0.0

        top_earners = sorted(
            list(employee_salaries.values()),
            key=lambda x: x['amount'],
            reverse=True
        )[:5]

        # Calculate percentage change
        if total_payroll_last > 0:
            payroll_change = ((total_payroll_current - total_payroll_last) / total_payroll_last) * 100
        else:
            payroll_change = 0.0

        data = {
            'cards': {
                'total_employees': total_employees,
                'active_contracts': active_contracts,
                'payslips_this_month': payslips_this_month,
                'total_payroll_current': round(total_payroll_current, 2),
                'total_payroll_last': round(total_payroll_last, 2),
                'payroll_change': round(payroll_change, 2),
                'pending_payslips': pending_payslips,
                'avg_salary': round(avg_salary, 2),
            },
            'monthly_chart': monthly_data,
            'top_earners': top_earners,
        }
        return request.make_response(
            json.dumps(data),
            headers=[('Content-Type', 'application/json')]
        )
