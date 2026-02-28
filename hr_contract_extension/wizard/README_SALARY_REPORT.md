# Salary Sheet Report Generator

## Overview
This wizard generates Excel salary sheet reports directly from Odoo's payroll, employee, and expense data. No need to upload external files - all data is pulled from your Odoo database.

## Features

### Data Sources
- **Employee Master Data**: Name, Code, DOB, DOJ, Aadhar, PAN, Mobile, UAN, ESIC
- **Payroll Data**: Salary components from validated payslips
- **Contract Information**: Basic salary, HRA, allowances
- **Statutory Deductions**: PF, ESIC, TDS from payslip calculations
- **Bank Details**: Account number and IFSC code

### Report Format
Generates Excel files matching the standard salary sheet format with:
- Company name and month header
- 50+ columns including:
  - Employee details (S.No, Code, Name, Father's Name, etc.)
  - Statutory information (Aadhar, PAN, UAN, ESIC)
  - Attendance (Worked days, Holidays, Leave)
  - Earnings (Basic, HRA, Allowances, Gross)
  - Deductions (PF, ESIC, TDS, Advance, Insurance)
  - Net salary and bank details

### Filters Available

#### Mandatory Filters
- **Salary Month**: Select the month for which to generate the report
- **Salary Year**: Year for the salary period
- **Company**: Company for which to generate the report

#### Optional Filters
- **Employees**: Select specific employees (leave empty for all)
- **Departments**: Filter by departments
- **Joining Date Range**: Include only employees who joined within a date range

## How to Use

### Step 1: Access the Wizard
Navigate to: **Payroll → Generate Salary Sheet**

### Step 2: Configure Report Parameters

#### Select Salary Period
- **Salary Month**: Choose the month (e.g., November)
- **Salary Year**: Enter the year (e.g., 2025)
- **Company**: Select your company

#### Apply Filters (Optional)
- **Employees**: Select specific employees or leave empty for all
- **Departments**: Filter by one or more departments
- **Joining Date From/To**: Filter employees by their joining date range

### Step 3: Generate Report
- Click **Generate Report** button
- The system will:
  - Fetch all employees matching your criteria
  - Retrieve payslips for the selected month/year
  - Extract salary components from payslip lines
  - Generate formatted Excel file

### Step 4: Download
- Once generation is complete, click **Download** button
- The Excel file will be downloaded with name format:
  `Salary_Sheet_[Month]_[Year]_[Company].xlsx`

## Report Structure

### Title Section
- Row 1: Company name
- Row 2: Month and year

### Header Row (Row 5)
Contains all column headers:
- Employee identification
- Statutory details
- Attendance information
- Earnings breakdown
- Deductions breakdown
- Net salary
- Bank details

### Data Rows (Row 6 onwards)
One row per employee with all salary details

## Data Mapping

### From Employee Master
- S.No: Auto-generated sequence
- Employee Code: `employee.employee_code`
- Name: `employee.name`
- PAN: `employee.pan_number`
- Aadhar: `employee.aadhar_number`
- Mobile: `employee.mobile_phone` or `employee.work_phone`
- DOB: `employee.birthday`
- DOJ: `employee.contract_id.date_start`
- UAN: `employee.uan_number`
- ESIC: `employee.esic_number`
- Category: `employee.job_id.name`
- Account No: `employee.bank_account_id.acc_number`
- IFSC: `employee.bank_account_id.bank_id.bic`

### From Payslip
- Worked Days: From worked days lines (code: WORK100)
- Basic Wages: Salary rule code: BASIC
- HRA: Salary rule code: HRA
- Gross: Salary rule code: GROSS
- EPF Employee: Salary rule code: PF
- ESIC Employee: Salary rule code: ESI
- TDS: Salary rule code: TDS
- Net Salary: Salary rule code: NET

## Use Cases

### 1. Monthly Payroll Report
- Select current month and year
- Leave all filters empty
- Generate report for all employees

### 2. Department-wise Report
- Select month and year
- Choose specific department(s)
- Generate report for that department only

### 3. New Joiners Report
- Select month and year
- Set joining date range (e.g., last month)
- Generate report showing only new employees

### 4. Specific Employees
- Select month and year
- Choose specific employees from the list
- Generate customized report

## Prerequisites

### Required Data in Odoo
1. **Employees**: Must have employee records with basic details
2. **Contracts**: Active contracts with salary structure
3. **Payslips**: Validated payslips for the selected period
4. **Salary Rules**: Standard salary rules with codes:
   - BASIC (Basic Salary)
   - HRA (House Rent Allowance)
   - GROSS (Gross Salary)
   - PF (Provident Fund)
   - ESI (ESIC)
   - TDS (Tax Deducted at Source)
   - NET (Net Salary)

### Python Library
- xlsxwriter (should be installed in venv)
- Check: `.\venv\Scripts\python.exe -m pip list | findstr xlsxwriter`
- Install if missing: `.\venv\Scripts\python.exe -m pip install xlsxwriter`

## Troubleshooting

### Error: "Required Python library (xlsxwriter) is not installed"
**Solution**: Install xlsxwriter in your venv:
```bash
.\venv\Scripts\python.exe -m pip install xlsxwriter
```

### Error: "No employees found matching the selected criteria"
**Solution**: Check your filters:
- Ensure employees exist in the selected company
- Verify department filter is not too restrictive
- Check joining date range is appropriate

### Error: "Invalid month or year specified"
**Solution**: 
- Ensure year is a valid 4-digit number
- Month should be selected from the dropdown

### Empty or Missing Data in Report
**Solution**:
- Verify payslips exist for the selected period
- Ensure payslips are in 'Done' or 'Paid' state
- Check that salary rules match the expected codes (BASIC, HRA, etc.)
- Verify employee master data is complete

### Missing Salary Components
**Solution**:
- Check if payslip has the required salary rule lines
- Verify salary rule codes match exactly (case-sensitive)
- Ensure payslip computation was successful

## Technical Notes

### Salary Rule Codes
The report expects these standard codes in payslips:
- `BASIC`: Basic salary
- `HRA`: House rent allowance
- `GROSS`: Gross salary
- `PF`: Employee PF deduction
- `ESI`: Employee ESIC deduction
- `TDS`: Tax deducted at source
- `NET`: Net salary payable

If your salary rules use different codes, update the `_get_rule_amount()` calls in the wizard.

### Worked Days Code
The report looks for worked days with code `WORK100`. If your system uses a different code, update line:
```python
worked_days = payslip.worked_days_line_ids.filtered(lambda l: l.code == 'WORK100')
```

### Date Formats
- DOB, DOJ, Exit Date: Formatted as DD.MM.YYYY
- Numbers: Formatted with thousand separators and 2 decimal places

## Customization

### Adding Custom Columns
To add custom columns to the report:
1. Add column header to the `headers` list
2. Add corresponding `worksheet.write()` call in the data loop
3. Adjust column width if needed

### Modifying Formats
Edit the format definitions in `_generate_excel_report()`:
- `title_format`: Title row styling
- `header_format`: Column header styling
- `data_format`: Text data styling
- `number_format`: Numeric data styling
- `date_format`: Date field styling

## Support
For issues or customization requests, contact your system administrator.
