# Salary Sheet Filter Wizard

## Overview
This wizard allows you to filter and generate customized salary sheets from your uploaded Excel files based on various criteria like employee selection, joining dates, and salary periods.

## Prerequisites

Before using this feature, you need to install the required Python libraries:

```bash
pip install xlrd xlsxwriter
```

## How to Use

### Step 1: Access the Wizard
- Navigate to: **Payroll → Filter Salary Sheet**

### Step 2: Upload Your Salary Sheet
- Click on the **Upload Excel File** field
- Select your salary sheet file (`.xls` or `.xlsx` format)
- The file should contain employee data with columns like:
  - Employee Code / Emp Code
  - Employee Name / Name
  - Date of Joining / DOJ
  - Salary components (Gross, Deductions, Net, TDS, etc.)

### Step 3: Apply Filters (Optional)

#### Filter by Employees
- Select specific employees from the **Filter by Employees** field
- Leave empty to include all employees

#### Filter by Joining Date
- **Joining Date From**: Include employees who joined on or after this date
- **Joining Date To**: Include employees who joined on or before this date

#### Filter by Salary Period
- **Salary Month**: Select the month for salary processing
- **Salary Year**: Enter the year (defaults to current year)

### Step 4: Generate Filtered Sheet
- Click **Generate Filtered Sheet** button
- The wizard will process your file and apply the selected filters

### Step 5: Download
- Once processing is complete, the **Download** button will appear
- Click **Download** to save the filtered Excel file
- The output file will be named: `Filtered_Salary_Sheet_[Month]_[Year].xlsx`

## Features

### Automatic Column Detection
The wizard automatically detects:
- Employee code/ID columns
- Employee name columns
- Joining date columns
- Other salary-related columns

### Smart Filtering
- **Employee Matching**: Matches by both employee code and name
- **Date Range Filtering**: Flexible date range selection
- **Preserve Formatting**: Maintains original Excel structure

### Output Format
- Excel format (`.xlsx`)
- Includes header row
- Contains only filtered employee records
- Ready for import or further processing

## Use Cases

### 1. Generate Monthly Payroll for Specific Department
- Upload full salary sheet
- Select employees from specific department
- Set salary month and year
- Generate filtered sheet for that department only

### 2. New Joiners Report
- Upload salary sheet
- Set joining date range (e.g., last month)
- Generate sheet with only new employees

### 3. Custom Employee Selection
- Upload salary sheet
- Select specific employees manually
- Generate personalized salary sheets

## Troubleshooting

### Error: "Required Python libraries are not installed"
**Solution**: Install the required libraries:
```bash
pip install xlrd xlsxwriter
```

### Error: "Could not identify header row"
**Solution**: Ensure your Excel file has a proper header row with column names like "Employee Code", "Name", "DOJ", etc.

### No data in filtered sheet
**Solution**: Check your filter criteria - they might be too restrictive. Try:
- Removing employee filter
- Expanding date range
- Checking if employee codes/names match exactly

## Technical Details

### Supported File Formats
- `.xls` (Excel 97-2003)
- `.xlsx` (Excel 2007+)

### Column Name Recognition
The wizard recognizes various column naming conventions:
- Employee: "Employee Code", "Emp Code", "Code", "Employee ID"
- Name: "Employee Name", "Emp Name", "Name"
- Joining Date: "Date of Joining", "DOJ", "Joining Date"

### Performance
- Processes files with thousands of employees efficiently
- Generates output in seconds

## Future Enhancements
- Support for multiple sheet filtering
- Advanced salary component filtering
- Batch processing for multiple files
- Export to PDF format
- Email filtered sheets directly

## Support
For issues or feature requests, contact your system administrator.
