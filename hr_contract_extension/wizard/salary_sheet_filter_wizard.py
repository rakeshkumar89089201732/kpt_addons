# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import io
from datetime import datetime

try:
    import xlrd
    import xlsxwriter
except ImportError:
    xlrd = None
    xlsxwriter = None


class SalarySheetFilterWizard(models.TransientModel):
    _name = 'salary.sheet.filter.wizard'
    _description = 'Salary Sheet Filter Wizard'

    file_data = fields.Binary('Upload Excel File', required=True, help='Upload the salary sheet Excel file (.xls or .xlsx)')
    file_name = fields.Char('File Name')
    
    # Filter fields
    employee_ids = fields.Many2many('hr.employee', string='Filter by Employees', help='Leave empty to include all employees')
    date_from = fields.Date('Joining Date From', help='Filter employees who joined from this date')
    date_to = fields.Date('Joining Date To', help='Filter employees who joined until this date')
    salary_month = fields.Selection([
        ('01', 'January'), ('02', 'February'), ('03', 'March'),
        ('04', 'April'), ('05', 'May'), ('06', 'June'),
        ('07', 'July'), ('08', 'August'), ('09', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December')
    ], string='Salary Month', help='Month for which salary is being processed')
    salary_year = fields.Char('Salary Year', default=lambda self: str(datetime.now().year), help='Year for salary processing')
    
    # Output
    output_file = fields.Binary('Filtered Salary Sheet', readonly=True)
    output_file_name = fields.Char('Output File Name', readonly=True)
    state = fields.Selection([('draft', 'Upload'), ('done', 'Done')], default='draft')

    def action_generate_filtered_sheet(self):
        """Generate filtered salary sheet based on selected criteria"""
        self.ensure_one()
        
        if not xlrd or not xlsxwriter:
            raise UserError('Required Python libraries (xlrd, xlsxwriter) are not installed. Please install them first:\npip install xlrd xlsxwriter')
        
        if not self.file_data:
            raise UserError('Please upload an Excel file first.')
        
        # Decode the uploaded file
        file_content = base64.b64decode(self.file_data)
        
        try:
            # Try to open as Excel file
            workbook = xlrd.open_workbook(file_contents=file_content)
            sheet = workbook.sheet_by_index(0)
            
            # Find header row (look for 'S No.' or 'S.No' column)
            header_row_idx = None
            headers = []
            title_rows = []  # Store rows before header for company name, month, etc.
            
            for row_idx in range(min(10, sheet.nrows)):
                row_values = sheet.row_values(row_idx)
                row_str = ' '.join([str(v).lower() for v in row_values if v])
                if 's.no' in row_str or 's no' in row_str or (row_values and str(row_values[0]).strip().lower() in ['s.no', 's no', 'sl no']):
                    header_row_idx = row_idx
                    headers = row_values
                    # Store all rows before header as title rows
                    for i in range(row_idx):
                        title_rows.append(sheet.row_values(i))
                    break
            
            if header_row_idx is None:
                raise UserError('Could not identify header row in the Excel file. Please ensure the file has proper column headers.')
            
            # Identify key columns based on actual structure
            serial_col = None
            emp_code_col = None
            emp_name_col = None
            joining_date_col = None
            dob_col = None
            
            for idx, header in enumerate(headers):
                if header:
                    h_lower = str(header).lower()
                    if 's.no' in h_lower or 's no' in h_lower:
                        serial_col = idx
                    elif 'employee code' in h_lower:
                        emp_code_col = idx
                    elif 'name' in h_lower and 'father' not in h_lower and 'husband' not in h_lower:
                        emp_name_col = idx
                    elif 'd.o.j' in h_lower or 'doj' in h_lower:
                        joining_date_col = idx
                    elif 'd.o.b' in h_lower or 'dob' in h_lower:
                        dob_col = idx
            
            # Prepare filtered data
            filtered_rows = []
            employee_count = 0
            
            for row_idx in range(header_row_idx + 1, sheet.nrows):
                row_values = sheet.row_values(row_idx)
                
                # Check if this is an employee row (has S.No)
                if serial_col is not None:
                    serial_val = row_values[serial_col] if serial_col < len(row_values) else None
                    
                    # Only process rows with valid serial numbers
                    if not (serial_val and str(serial_val).strip() and str(serial_val).strip().replace('.', '').replace(',', '').isdigit()):
                        continue
                
                # Apply filters
                include_row = True
                
                # Filter by employee
                if self.employee_ids:
                    emp_code = row_values[emp_code_col] if emp_code_col is not None and emp_code_col < len(row_values) else None
                    emp_name = row_values[emp_name_col] if emp_name_col is not None and emp_name_col < len(row_values) else None
                    
                    # Check if this employee is in the filter list
                    employee_match = False
                    for emp in self.employee_ids:
                        if (emp_code and str(emp_code).strip() == str(emp.employee_code or '').strip()) or \
                           (emp_name and str(emp_name).strip().lower() == str(emp.name or '').strip().lower()):
                            employee_match = True
                            break
                    
                    if not employee_match:
                        include_row = False
                
                # Filter by joining date
                if include_row and (self.date_from or self.date_to) and joining_date_col is not None:
                    joining_date_val = row_values[joining_date_col] if joining_date_col < len(row_values) else None
                    
                    if joining_date_val:
                        try:
                            # Try to parse date (Excel dates are stored as numbers or strings)
                            if isinstance(joining_date_val, (int, float)):
                                joining_date = xlrd.xldate_as_datetime(joining_date_val, workbook.datemode).date()
                            else:
                                # Try to parse string date in DD.MM.YYYY format
                                date_str = str(joining_date_val).strip()
                                if '.' in date_str:
                                    parts = date_str.split('.')
                                    if len(parts) == 3:
                                        joining_date = datetime(int(parts[2]), int(parts[1]), int(parts[0])).date()
                                else:
                                    joining_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                            
                            if self.date_from and joining_date < self.date_from:
                                include_row = False
                            if self.date_to and joining_date > self.date_to:
                                include_row = False
                        except:
                            pass  # If date parsing fails, include the row
                
                if include_row:
                    employee_count += 1
                    filtered_rows.append(row_values)
            
            # Generate output Excel file with exact same format
            output = io.BytesIO()
            workbook_out = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook_out.add_worksheet('Salary Sheet')
            
            # Define formats
            header_format = workbook_out.add_format({
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'bg_color': '#D9E1F2'
            })
            
            title_format = workbook_out.add_format({
                'bold': True,
                'align': 'center',
                'font_size': 12
            })
            
            data_format = workbook_out.add_format({
                'border': 1,
                'align': 'left',
                'valign': 'vcenter'
            })
            
            number_format = workbook_out.add_format({
                'border': 1,
                'align': 'right',
                'num_format': '#,##0.00'
            })
            
            # Write title rows (company name, month, etc.)
            current_row = 0
            for title_row in title_rows:
                for col_idx, cell_value in enumerate(title_row):
                    if cell_value:
                        worksheet.write(current_row, col_idx, cell_value, title_format)
                current_row += 1
            
            # Write header row
            for col_idx, header in enumerate(headers):
                if header:
                    worksheet.write(current_row, col_idx, header, header_format)
            current_row += 1
            
            # Write filtered employee data
            for row_data in filtered_rows:
                for col_idx, cell_value in enumerate(row_data):
                    if cell_value:
                        # Use number format for numeric columns
                        if isinstance(cell_value, (int, float)):
                            worksheet.write(current_row, col_idx, cell_value, number_format)
                        else:
                            worksheet.write(current_row, col_idx, cell_value, data_format)
                current_row += 1
            
            # Set column widths to match original
            worksheet.set_column(0, 0, 6)   # S.No
            worksheet.set_column(1, 1, 12)  # Emp Code
            worksheet.set_column(3, 3, 25)  # Name
            worksheet.set_column(4, 4, 25)  # Father's Name
            worksheet.set_column(6, 6, 15)  # Aadhar
            worksheet.set_column(7, 7, 12)  # Mobile
            worksheet.set_column(8, 10, 12) # DOB, DOJ, Exit
            worksheet.set_column(11, 12, 15) # UAN, ESIC
            worksheet.set_column(21, 55, 12) # All salary columns
            
            workbook_out.close()
            output.seek(0)
            
            # Prepare output file name
            month_name = dict(self._fields['salary_month'].selection).get(self.salary_month, '') if self.salary_month else 'All'
            output_name = f'Filtered_Salary_Sheet_{month_name}_{self.salary_year or "All"}.xlsx'
            
            self.write({
                'output_file': base64.b64encode(output.read()),
                'output_file_name': output_name,
                'state': 'done'
            })
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'salary.sheet.filter.wizard',
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'new',
                'context': self.env.context,
            }
            
        except Exception as e:
            raise UserError(f'Error processing Excel file: {str(e)}')
    
    def action_download_filtered_sheet(self):
        """Download the generated filtered sheet"""
        self.ensure_one()
        
        if not self.output_file:
            raise UserError('No filtered sheet available. Please generate it first.')
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=salary.sheet.filter.wizard&id={self.id}&field=output_file&download=true&filename={self.output_file_name}',
            'target': 'self',
        }
