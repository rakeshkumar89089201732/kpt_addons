# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import io
from datetime import datetime
from dateutil.relativedelta import relativedelta

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class SalarySheetReportWizard(models.TransientModel):
    _name = 'salary.sheet.report.wizard'
    _description = 'Salary Sheet Report Generator'

    # Filter fields
    employee_ids = fields.Many2many('hr.employee', string='Employees', help='Leave empty to include all employees')
    department_ids = fields.Many2many('hr.department', string='Departments', help='Filter by departments')
    date_from = fields.Date('Joining Date From', help='Filter employees who joined from this date')
    date_to = fields.Date('Joining Date To', help='Filter employees who joined until this date')
    
    # Salary period
    salary_month = fields.Selection([
        ('01', 'January'), ('02', 'February'), ('03', 'March'),
        ('04', 'April'), ('05', 'May'), ('06', 'June'),
        ('07', 'July'), ('08', 'August'), ('09', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December')
    ], string='Salary Month', required=True, default=lambda self: str(datetime.now().month).zfill(2))
    salary_year = fields.Char('Salary Year', required=True, default=lambda self: str(datetime.now().year))

    # When enabled, employees are grouped under their manager,
    # with a highlighted manager header row in the Excel.
    group_by_manager = fields.Boolean(string='Group by Manager', default=True)
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    # Preview lines (for on-screen list & standard Odoo export)
    line_ids = fields.One2many('salary.sheet.report.line', 'wizard_id', string='Preview Lines', readonly=True)

    # Output
    output_file = fields.Binary('Salary Sheet', readonly=True)
    output_file_name = fields.Char('File Name', readonly=True)
    state = fields.Selection([('draft', 'Configure'), ('done', 'Done')], default='draft')

    # -------------------------------------------------------------------------
    # Preview in list view
    # -------------------------------------------------------------------------
    def action_generate_preview(self):
        """Generate preview lines and open them in a list view.

        User can then use the standard Odoo 'Export' action to export only the
        columns they are interested in.
        """
        self.ensure_one()

        # Compute the same period as for the Excel
        try:
            year = int(self.salary_year)
            month = int(self.salary_month)
            date_from = datetime(year, month, 1).date()
            date_to = (date_from + relativedelta(months=1, days=-1))
        except Exception:
            raise UserError('Invalid month or year specified.')

        employees = self._get_filtered_employees()
        if not employees:
            raise UserError('No employees found matching the selected criteria.')

        payslips = self._get_payslips_for_period(employees, date_from, date_to)

        # Clear existing preview lines for this wizard
        self.line_ids.unlink()

        # Reuse the same grouping logic as the Excel report
        def _iter_employees_grouped():
            if not self.group_by_manager:
                yield (False, employees)
                return

            buckets = {}
            for emp in employees:
                mgr = emp.parent_id
                key = mgr.id if mgr else 0
                buckets.setdefault(key, {'manager': mgr, 'employees': self.env['hr.employee']})
                buckets[key]['employees'] |= emp

            def _mgr_sort_key(item):
                mgr = item['manager']
                return (0 if mgr else 1, (mgr.name or '') if mgr else 'ZZZ')

            for item in sorted(buckets.values(), key=_mgr_sort_key):
                yield (item['manager'], item['employees'].sorted(lambda e: (e.name or '').lower()))

        line_vals = []
        for manager, emp_group in _iter_employees_grouped():
            for employee in emp_group:
                emp_payslips = payslips.filtered(lambda p: p.employee_id == employee)
                contract = employee.contract_id

                # --- Salary figures (same logic as Excel, but summarised) ---
                basic = self._get_rule_amount(emp_payslips, 'BASIC')
                hra = self._get_rule_amount(emp_payslips, 'HRA')
                conveyance = self._get_rule_amount(emp_payslips, 'CA')
                gross = self._get_rule_amount(emp_payslips, 'GROSS')
                pf_employee = self._get_rule_amount(emp_payslips, 'PF')
                esic_employee = self._get_rule_amount(emp_payslips, 'ESI')
                tds = self._get_rule_amount(emp_payslips, 'TDS')
                net = self._get_rule_amount(emp_payslips, 'NET')

                if contract:
                    if not basic and contract.wage:
                        basic = contract.wage
                    if not hra and hasattr(contract, 'house_rent_allowance'):
                        hra = contract.house_rent_allowance or 0.0
                    if not conveyance and hasattr(contract, 'conveyance_allowance'):
                        conveyance = contract.conveyance_allowance or 0.0
                    if not gross and contract.wage:
                        gross = contract.wage + hra + conveyance
                    if not net and contract.wage:
                        net = contract.wage + hra + conveyance

                # Worked days: from payslip, then attendance fallback
                worked_days = emp_payslips.worked_days_line_ids.filtered(
                    lambda l: l.code in ('WORK100', 'WORK', 'WORKED')
                )
                days_worked = sum(worked_days.mapped('number_of_days')) if worked_days else 0.0
                if not days_worked:
                    attendances = self.env['hr.attendance'].search([
                        ('employee_id', '=', employee.id),
                        ('check_in', '>=', date_from),
                        ('check_in', '<=', date_to),
                    ])
                    if attendances:
                        days_worked = len({att.check_in.date() for att in attendances if att.check_in})

                # Bank details are simplified preview values
                bank_account = ''
                bank_rec = None
                if getattr(employee, 'bank_account_id', False) and employee.bank_account_id:
                    bank_rec = employee.bank_account_id
                elif getattr(employee, 'address_home_id', False) and employee.address_home_id and employee.address_home_id.bank_account_id:
                    bank_rec = employee.address_home_id.bank_account_id
                elif getattr(employee, 'address_home_id', False) and employee.address_home_id and getattr(employee.address_home_id, 'bank_ids', False):
                    bank_rec = employee.address_home_id.bank_ids[:1]
                if not bank_rec and getattr(employee, 'address_home_id', False) and employee.address_home_id:
                    bank_rec = self.env['res.partner.bank'].search([('partner_id', '=', employee.address_home_id.id)], limit=1)

                if bank_rec:
                    bank_account = bank_rec.acc_number or ''

                ifsc = ''
                if hasattr(employee, 'ifsc_code') and employee.ifsc_code:
                    ifsc = employee.ifsc_code
                elif bank_rec and bank_rec.bank_id:
                    ifsc = bank_rec.bank_id.bic or getattr(bank_rec.bank_id, 'ifsc_code', '') or ''

                emp_code = (
                    getattr(employee, 'employee_code', False)
                    or getattr(employee, 'barcode', False)
                    or getattr(employee, 'identification_id', False)
                    or ''
                )

                line_vals.append({
                    'wizard_id': self.id,
                    'employee_id': employee.id,
                    'manager_id': manager.id if manager else False,
                    'emp_code': emp_code,
                    'department_id': employee.department_id.id,
                    'category': employee.job_id.name if employee.job_id else '',
                    'worked_days': days_worked,
                    'basic': basic,
                    'hra': hra,
                    'conveyance': conveyance,
                    'gross': gross,
                    'net': net,
                    'pf_employee': pf_employee,
                    'esic_employee': esic_employee,
                    'tds': tds,
                    'bank_account': bank_account,
                    'ifsc': ifsc,
                })

        if line_vals:
            self.env['salary.sheet.report.line'].create(line_vals)

        # Open the preview lines in a dedicated list view so the user can use
        # the standard "Export" action and choose which columns to export.
        return {
            'type': 'ir.actions.act_window',
            'name': 'Salary Sheet Preview',
            'res_model': 'salary.sheet.report.line',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('wizard_id', '=', self.id)],
            'context': {'group_by': ['manager_id'] if self.group_by_manager else []},
        }

    def action_generate_salary_sheet(self):
        """Generate salary sheet Excel report from Odoo payroll data"""
        self.ensure_one()
        
        if not xlsxwriter:
            raise UserError('Required Python library (xlsxwriter) is not installed. Please install it:\npip install xlsxwriter')
        
        # Build date range for the selected month
        try:
            year = int(self.salary_year)
            month = int(self.salary_month)
            date_from = datetime(year, month, 1).date()
            date_to = (date_from + relativedelta(months=1, days=-1))
        except:
            raise UserError('Invalid month or year specified.')
        
        # Get employees based on filters
        employees = self._get_filtered_employees()
        
        if not employees:
            raise UserError('No employees found matching the selected criteria.')
        
        # Get payslips for the selected period
        payslips = self._get_payslips_for_period(employees, date_from, date_to)
        
        # Generate Excel file
        output = self._generate_excel_report(employees, payslips, date_from, date_to)
        
        # Prepare output file name
        month_name = dict(self._fields['salary_month'].selection).get(self.salary_month, '')
        output_name = f'Salary_Sheet_{month_name}_{self.salary_year}_{self.company_id.name}.xlsx'

        output_b64 = base64.b64encode(output.getvalue())

        # Persist: store as attachment so it can be downloaded later.
        attach_model = 'res.company'
        attach_res_id = self.company_id.id
        if self.employee_ids and len(self.employee_ids) == 1:
            attach_model = 'hr.employee'
            attach_res_id = self.employee_ids.id

        self.env['ir.attachment'].create({
            'name': output_name,
            'type': 'binary',
            'datas': output_b64,
            'res_model': attach_model,
            'res_id': attach_res_id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        
        self.write({
            'output_file': output_b64,
            'output_file_name': output_name,
            'state': 'done'
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'salary.sheet.report.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context,
        }
    
    def _get_filtered_employees(self):
        """Get employees based on filter criteria"""
        domain = [('company_id', '=', self.company_id.id)]
        
        if self.employee_ids:
            domain.append(('id', 'in', self.employee_ids.ids))
        
        if self.department_ids:
            domain.append(('department_id', 'in', self.department_ids.ids))
        
        employees = self.env['hr.employee'].search(domain, order='name')
        
        # Filter by joining date if specified
        if self.date_from or self.date_to:
            filtered_employees = self.env['hr.employee']
            for emp in employees:
                # Get joining date from contract or employee
                joining_date = None
                if emp.contract_id and emp.contract_id.date_start:
                    joining_date = emp.contract_id.date_start
                elif emp.contract_ids:
                    first_contract = emp.contract_ids.sorted('date_start')[0]
                    joining_date = first_contract.date_start
                
                if joining_date:
                    if self.date_from and joining_date < self.date_from:
                        continue
                    if self.date_to and joining_date > self.date_to:
                        continue
                
                filtered_employees |= emp
            
            return filtered_employees
        
        return employees
    
    def _get_payslips_for_period(self, employees, date_from, date_to):
        """Get payslips for the selected period"""
        if not employees:
            return self.env['hr.payslip']
        
        domain = [
            ('employee_id', 'in', employees.ids),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
            ('state', 'in', ['done', 'paid']),
        ]
        
        return self.env['hr.payslip'].search(domain)
    
    def _generate_excel_report(self, employees, payslips, date_from, date_to):
        """Generate Excel file with salary sheet data"""
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Salary Sheet')
        
        # Page setup for A4 landscape printing and fit-to-page
        worksheet.set_landscape()
        # A4 paper size code in Excel/XlsxWriter is 9
        worksheet.set_paper(9)
        # Narrow margins for better fit on A4
        worksheet.set_margins(left=0.25, right=0.25, top=0.5, bottom=0.5)
        # Center horizontally on page
        worksheet.center_horizontally()
        # Fit the sheet to 1 page wide by 1 page tall
        worksheet.fit_to_pages(1, 1)
        
        # Define formats
        title_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'font_size': 14,
            'bg_color': '#D9E1F2'
        })
        
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'text_wrap': True
        })
        
        data_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter'
        })
        
        number_format = workbook.add_format({
            'border': 1,
            'align': 'right',
            'num_format': '#,##0.00'
        })
        
        date_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'num_format': 'dd.mm.yyyy'
        })
        
        # Write title
        month_name = dict(self._fields['salary_month'].selection).get(self.salary_month, '')
        worksheet.merge_range('A1:AH1', f'Name of the Factory - {self.company_id.name}', title_format)
        worksheet.merge_range('A2:AH2', f'Month of {month_name} {self.salary_year}', title_format)
        
        # Define column headers matching the reference Excel structure
        headers = [
            'S No.', 'Employee Code', 'Unit No.', 'Name', "Father's / Husband Name",
            'PAN No.', 'Aadhar No.', 'Mobile No.', 'D.O.B.', 'D.O.J.', 'D.O. Exit',
            'UAN NO', 'ESIC NO', 'Category', 'Worked Days', 'E.L', 'C.L', 'Holidays',
            'Total Days', 'Days', 'Over Time', 'Basic Wages', 'H.R.A', 'Conv.Allo',
            'Total Wages', 'Basic Wages', 'H.R.A', 'Conv.Allo', 'O.T.Amount',
            'Food Allowance', 'Total Wages', 'Incentive', 'EPF Employee', 'ESIC Employee',
            'T.D.S.', 'EPF Employer', 'Advance', 'Insurance', 'Total Deduction',
            'Bonus', 'Travelling', 'Incentive', 'Room Rent', 'Less: Insurance',
            'Food Allowance', 'Net Salary', 'EPF', 'ESI', 'Signature', 'Remark',
            'Account No.', 'IFSC Code'
        ]
        last_col_idx = len(headers) - 1
        
        # Write headers
        for col_idx, header in enumerate(headers):
            worksheet.write(4, col_idx, header, header_format)
        
        # Set column widths
        worksheet.set_column(0, 0, 6)   # S.No
        worksheet.set_column(1, 1, 12)  # Emp Code
        worksheet.set_column(3, 3, 25)  # Name
        worksheet.set_column(4, 4, 25)  # Father's Name
        worksheet.set_column(6, 6, 15)  # Aadhar
        worksheet.set_column(7, 7, 12)  # Mobile
        worksheet.set_column(8, 10, 12) # DOB, DOJ, Exit
        worksheet.set_column(11, 12, 15) # UAN, ESIC
        worksheet.set_column(21, 50, 12) # All salary columns
        
        # Write employee data
        row = 5
        # Repeat title + header rows when printing
        try:
            worksheet.repeat_rows(0, 4)
        except Exception:
            pass

        manager_header_format = workbook.add_format({
            'bold': True,
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'bg_color': '#E7E6E6',
        })

        def _guardian_display(emp):
            # Prefer custom guardian fields if installed
            rel = getattr(emp, 'guardian_relation', False)
            name = getattr(emp, 'guardian_name', False)
            if rel and name:
                label = dict(emp._fields.get('guardian_relation').selection).get(rel, rel)
                return f"{label}: {name}"
            # Backward compatible fallback
            return (
                getattr(emp, 'father_name', False)
                or getattr(emp, 'father_husband_name', False)
                or ''
            )

        def _iter_employees_grouped():
            if not self.group_by_manager:
                yield (False, employees)
                return

            buckets = {}
            for emp in employees:
                mgr = emp.parent_id
                key = mgr.id if mgr else 0
                buckets.setdefault(key, {'manager': mgr, 'employees': self.env['hr.employee']})
                buckets[key]['employees'] |= emp

            def _mgr_sort_key(item):
                mgr = item['manager']
                return (0 if mgr else 1, (mgr.name or '') if mgr else 'ZZZ')

            for item in sorted(buckets.values(), key=_mgr_sort_key):
                # sort employees by name within each manager bucket
                yield (item['manager'], item['employees'].sorted(lambda e: (e.name or '').lower()))

        serial = 1
        for manager, emp_group in _iter_employees_grouped():
            if manager or self.group_by_manager:
                mgr_name = manager.name if manager else 'No Manager'
                worksheet.merge_range(row, 0, row, last_col_idx, f"Manager: {mgr_name}", manager_header_format)
                row += 1

            for employee in emp_group:
                payslip = payslips.filtered(lambda p: p.employee_id == employee)

                contract = employee.contract_id

                # --- Salary figures from payslip rules (with sensible fallbacks) ---
                basic = self._get_rule_amount(payslip, 'BASIC')
                hra = self._get_rule_amount(payslip, 'HRA')
                # Conveyance Allowance rule code from tds_salary_rule.xml is "CA"
                conveyance = self._get_rule_amount(payslip, 'CA')
                gross = self._get_rule_amount(payslip, 'GROSS')
                pf_employee = self._get_rule_amount(payslip, 'PF')
                esic_employee = self._get_rule_amount(payslip, 'ESI')
                tds = self._get_rule_amount(payslip, 'TDS')
                net = self._get_rule_amount(payslip, 'NET')

                # If payslip / rules are missing, fallback to contract values
                if contract:
                    # Basic from contract wage when not present on payslip
                    if not basic and contract.wage:
                        basic = contract.wage
                    # HRA from contract.house_rent_allowance
                    if not hra and hasattr(contract, 'house_rent_allowance'):
                        hra = contract.house_rent_allowance or 0.0
                    # Conveyance from contract.conveyance_allowance
                    if not conveyance and hasattr(contract, 'conveyance_allowance'):
                        conveyance = contract.conveyance_allowance or 0.0
                    # Gross and Net as combined amount when not explicitly on payslip
                    if not gross and contract.wage:
                        gross = contract.wage + hra + conveyance
                    if not net and contract.wage:
                        net = contract.wage + hra + conveyance

                # Worked days: try to take real "worked" days from payslip
                worked_days = payslip.worked_days_line_ids.filtered(
                    lambda l: l.code in ('WORK100', 'WORK', 'WORKED')
                ) if payslip else self.env['hr.payslip.worked_days']
                days_worked = sum(worked_days.mapped('number_of_days')) if worked_days else 0

                # If payslip has no worked days, fallback to attendance for the month
                if not days_worked:
                    attendances = self.env['hr.attendance'].search([
                        ('employee_id', '=', employee.id),
                        ('check_in', '>=', date_from),
                        ('check_in', '<=', date_to),
                    ])
                    if attendances:
                        # Count distinct calendar days with at least one check_in
                        days_worked = len({att.check_in.date() for att in attendances if att.check_in})
                
                col = 0
                worksheet.write(row, col, serial, data_format); col += 1  # S.No
                emp_code = (
                    getattr(employee, 'employee_code', False)
                    or getattr(employee, 'barcode', False)
                    or getattr(employee, 'identification_id', False)
                    or ''
                )
                worksheet.write(row, col, emp_code, data_format); col += 1  # Emp Code
                worksheet.write(row, col, '', data_format); col += 1  # Unit No
                worksheet.write(row, col, employee.name or '', data_format); col += 1  # Name
                worksheet.write(row, col, _guardian_display(employee) or '', data_format); col += 1  # Father's / Husband Name
                pan_val = (
                    getattr(employee, 'pan_number', False)
                    or getattr(employee, 'pan_no', False)
                    or getattr(employee, 'pan', False)
                    or ''
                )
                worksheet.write(row, col, pan_val, data_format); col += 1  # PAN
                aadhar_val = (
                    getattr(employee, 'aadhar_number', False)
                    or getattr(employee, 'aadhar_no', False)
                    or getattr(employee, 'aadhaar_no', False)
                    or ''
                )
                worksheet.write(row, col, aadhar_val, data_format); col += 1  # Aadhar
                mobile_val = (
                    getattr(employee, 'mobile_phone', False)
                    or getattr(employee, 'work_phone', False)
                    or (employee.address_home_id.mobile if getattr(employee, 'address_home_id', False) else False)
                    or ''
                )
                worksheet.write(row, col, mobile_val, data_format); col += 1  # Mobile
                
                if getattr(employee, 'birthday', False):
                    try:
                        from datetime import datetime as _dt
                        dt_val = _dt.combine(employee.birthday, _dt.min.time())
                        worksheet.write_datetime(row, col, dt_val, date_format)
                    except Exception:
                        worksheet.write(row, col, str(employee.birthday), data_format)
                else:
                    worksheet.write(row, col, '', data_format)
                col += 1  # DOB
                
                if contract and contract.date_start:
                    try:
                        from datetime import datetime as _dt
                        dt_val = _dt.combine(contract.date_start, _dt.min.time())
                        worksheet.write_datetime(row, col, dt_val, date_format)
                    except Exception:
                        worksheet.write(row, col, str(contract.date_start), data_format)
                else:
                    worksheet.write(row, col, '', data_format)
                col += 1  # DOJ
                
                if contract and contract.date_end:
                    try:
                        from datetime import datetime as _dt
                        dt_val = _dt.combine(contract.date_end, _dt.min.time())
                        worksheet.write_datetime(row, col, dt_val, date_format)
                    except Exception:
                        worksheet.write(row, col, str(contract.date_end), data_format)
                else:
                    worksheet.write(row, col, '', data_format)
                col += 1  # Exit Date
                
                uan_val = getattr(employee, 'uan_number', False) or getattr(employee, 'uan', False) or ''
                esic_val = getattr(employee, 'esic_number', False) or getattr(employee, 'esic_no', False) or getattr(employee, 'ip_no', False) or ''
                worksheet.write(row, col, uan_val, data_format); col += 1  # UAN
                worksheet.write(row, col, esic_val, data_format); col += 1  # ESIC
                worksheet.write(row, col, employee.job_id.name if employee.job_id else '', data_format); col += 1  # Category
                worksheet.write(row, col, days_worked, number_format); col += 1  # Worked Days
                worksheet.write(row, col, 0, number_format); col += 1  # EL
                worksheet.write(row, col, 0, number_format); col += 1  # CL
                worksheet.write(row, col, 0, number_format); col += 1  # Holidays
                worksheet.write(row, col, days_worked, number_format); col += 1  # Total Days
                worksheet.write(row, col, days_worked, number_format); col += 1  # Days
                worksheet.write(row, col, 0, number_format); col += 1  # OT
                worksheet.write(row, col, basic, number_format); col += 1  # Basic
                worksheet.write(row, col, hra, number_format); col += 1  # HRA
                worksheet.write(row, col, conveyance, number_format); col += 1  # Conv Allo
                total_wages = gross if gross else (basic + hra + conveyance)
                worksheet.write(row, col, total_wages, number_format); col += 1  # Total Wages
                worksheet.write(row, col, basic, number_format); col += 1  # Basic (earned)
                worksheet.write(row, col, hra, number_format); col += 1  # HRA (earned)
                worksheet.write(row, col, conveyance, number_format); col += 1  # Conv Allo (earned)
                worksheet.write(row, col, 0, number_format); col += 1  # OT Amount
                worksheet.write(row, col, 0, number_format); col += 1  # Food Allowance
                total_wages_earned = gross if gross else (basic + hra + conveyance)
                worksheet.write(row, col, total_wages_earned, number_format); col += 1  # Total Wages (earned)
                worksheet.write(row, col, 0, number_format); col += 1  # Incentive
                worksheet.write(row, col, pf_employee, number_format); col += 1  # EPF Employee
                worksheet.write(row, col, esic_employee, number_format); col += 1  # ESIC Employee
                worksheet.write(row, col, tds, number_format); col += 1  # TDS
                worksheet.write(row, col, pf_employee, number_format); col += 1  # EPF Employer
                worksheet.write(row, col, 0, number_format); col += 1  # Advance
                worksheet.write(row, col, 0, number_format); col += 1  # Insurance
                worksheet.write(row, col, pf_employee + esic_employee + tds, number_format); col += 1  # Total Deduction
                worksheet.write(row, col, 0, number_format); col += 1  # Bonus
                worksheet.write(row, col, 0, number_format); col += 1  # Travelling
                worksheet.write(row, col, 0, number_format); col += 1  # Incentive
                worksheet.write(row, col, 0, number_format); col += 1  # Room Rent
                worksheet.write(row, col, 0, number_format); col += 1  # Less Insurance
                worksheet.write(row, col, 0, number_format); col += 1  # Food Allowance
                worksheet.write(row, col, net, number_format); col += 1  # Net Salary
                worksheet.write(row, col, pf_employee, number_format); col += 1  # EPF
                worksheet.write(row, col, esic_employee, number_format); col += 1  # ESI
                worksheet.write(row, col, '', data_format); col += 1  # Signature
                worksheet.write(row, col, '', data_format); col += 1  # Remark
                # ---------- Bank details (Account No. & IFSC) ----------
                acc_num = ''
                bank_rec = None
                # 1) Direct bank_account_id on employee (most common)
                if getattr(employee, 'bank_account_id', False) and employee.bank_account_id:
                    bank_rec = employee.bank_account_id
                # 2) Bank account on home address partner (bank_account_id helper)
                elif getattr(employee, 'address_home_id', False) and employee.address_home_id and employee.address_home_id.bank_account_id:
                    bank_rec = employee.address_home_id.bank_account_id
                # 3) Any bank account linked to home address partner (bank_ids one2many)
                elif getattr(employee, 'address_home_id', False) and employee.address_home_id and getattr(employee.address_home_id, 'bank_ids', False):
                    bank_rec = employee.address_home_id.bank_ids[:1]
                # 4) As a last resort, try any bank account whose partner is the home address
                if not bank_rec and getattr(employee, 'address_home_id', False) and employee.address_home_id:
                    bank_rec = self.env['res.partner.bank'].search([('partner_id', '=', employee.address_home_id.id)], limit=1)

                # 5) Custom bank account number field directly on employee (if you use one)
                if not bank_rec and hasattr(employee, 'bank_account_number'):
                    acc_num = getattr(employee, 'bank_account_number') or ''
                elif bank_rec:
                    acc_num = bank_rec.acc_number or ''
                worksheet.write(row, col, acc_num, data_format); col += 1  # Account

                ifsc = ''
                # Prefer explicit IFSC on employee if defined (from hr_employee_extention)
                if hasattr(employee, 'ifsc_code') and employee.ifsc_code:
                    ifsc = employee.ifsc_code
                elif bank_rec and bank_rec.bank_id:
                    # In Indian setups IFSC is often stored in bic or a custom field on the bank.
                    ifsc = bank_rec.bank_id.bic or getattr(bank_rec.bank_id, 'ifsc_code', '') or ''
                worksheet.write(row, col, ifsc, data_format)  # IFSC
                
                row += 1
                serial += 1
        
        # Define print area to the used range
        try:
            worksheet.print_area(0, 0, max(row - 1, 0), last_col_idx)
        except Exception:
            pass
        workbook.close()
        output.seek(0)
        return output
    
    def _get_rule_amount(self, payslips, rule_code):
        """Get salary rule amount from payslip recordset (sum if many)."""
        if not payslips:
            return 0.0
        lines = payslips.mapped('line_ids').filtered(lambda l: l.code == rule_code)
        return sum(abs(l.total or 0.0) for l in lines) if lines else 0.0
    
    def action_download(self):
        """Download the generated report"""
        self.ensure_one()
        
        if not self.output_file:
            raise UserError('No report available. Please generate it first.')
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=salary.sheet.report.wizard&id={self.id}&field=output_file&download=true&filename={self.output_file_name}',
            'target': 'self',
        }

    def action_new(self):
        """Open a fresh instance of the wizard (used by 'Generate Another' button)."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'salary.sheet.report.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }


class SalarySheetReportLine(models.TransientModel):
    """Lightweight preview line used to show salary data in a list view.

    Users can then use Odoo's standard Export feature to export only the
    columns they are interested in.
    """
    _name = 'salary.sheet.report.line'
    _description = 'Salary Sheet Preview Line'

    wizard_id = fields.Many2one('salary.sheet.report.wizard', ondelete='cascade')

    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    manager_id = fields.Many2one('hr.employee', string='Manager', readonly=True)
    emp_code = fields.Char(string='Employee Code', readonly=True)
    department_id = fields.Many2one('hr.department', string='Department', readonly=True)
    category = fields.Char(string='Category', readonly=True)

    worked_days = fields.Float(string='Worked Days', readonly=True)
    basic = fields.Float(string='Basic Wages', readonly=True)
    hra = fields.Float(string='HRA', readonly=True)
    conveyance = fields.Float(string='Conveyance Allowance', readonly=True)
    gross = fields.Float(string='Gross Wages', readonly=True)
    net = fields.Float(string='Net Salary', readonly=True)

    pf_employee = fields.Float(string='EPF Employee', readonly=True)
    esic_employee = fields.Float(string='ESIC Employee', readonly=True)
    tds = fields.Float(string='TDS', readonly=True)

    bank_account = fields.Char(string='Account No.', readonly=True)
    ifsc = fields.Char(string='IFSC Code', readonly=True)
