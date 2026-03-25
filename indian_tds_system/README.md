# Indian TDS System

A comprehensive Tax Deducted at Source (TDS) management system for Indian companies using Odoo.

## Features

### Core TDS Management
- **Complete TDS Calculation Engine**: Supports both Old and New tax regimes with automatic tax calculations
- **Progressive Tax Slabs**: Configurable tax slabs with surcharge and cess calculations
- **Section-wise Deductions**: Support for all major deduction sections (80C, 80D, 80E, 80G, etc.)
- **Age-based Tax Calculations**: Different tax slabs for regular, senior, and super senior citizens

### Employee Self-Service
- **Tax Planning Portal**: Employees can declare investments and plan their tax savings
- **Real-time Tax Calculations**: Instant calculation of tax liability and monthly TDS
- **Document Management**: Upload and manage investment proofs and declarations

### Compliance & Reporting
- **TDS Certificates (Form 16)**: Automated generation of TDS certificates
- **Quarterly Returns (24Q)**: Preparation and filing of quarterly TDS returns
- **Challan Management**: Track TDS deposits and reconciliation
- **Audit Trail**: Complete audit trail of all TDS transactions

### Integration
- **HR & Payroll Integration**: Seamless integration with Odoo HR and Payroll modules
- **Contract Management**: Automatic salary component breakdown for TDS calculations
- **Multi-company Support**: Support for multiple companies with separate TDS configurations

## Installation

1. Copy the module to your Odoo addons directory:
   ```
   cp -r indian_tds_system /path/to/odoo/addons/
   ```

2. Update the addons list and install the module:
   ```
   # From Odoo interface: Apps > Update Apps List > Search "Indian TDS System" > Install
   ```

3. Configure tax slabs and sections:
   - Go to TDS > Configuration > Tax Slabs
   - Go to TDS > Configuration > TDS Sections

## Configuration

### Tax Slabs Setup
1. Navigate to **TDS > Configuration > Tax Slabs**
2. Create tax slabs for different financial years and regimes
3. Configure slab lines with income ranges and tax rates
4. Set up rebate and surcharge configurations

### TDS Sections Setup
1. Navigate to **TDS > Configuration > TDS Sections**
2. Configure deduction sections (80C, 80D, etc.)
3. Set maximum limits and applicable regimes
4. Create sub-sections for detailed categorization

### Employee Setup
1. Go to **HR > Employees**
2. Add PAN and Aadhar numbers for employees
3. Set preferred tax regime
4. Configure salary components in contracts

## Usage

### TDS Calculation Process
1. **Create TDS Calculation**: 
   - Go to TDS > Calculations > TDS Calculations
   - Create new calculation for employee and financial year
   - System auto-fills salary and contract details

2. **Add Deductions**:
   - Add investment declarations under deduction lines
   - Upload supporting documents
   - System validates against section limits

3. **Calculate Tax**:
   - Click "Calculate TDS" to compute tax liability
   - Review monthly breakdown and projections
   - Approve calculation when finalized

4. **Generate Certificate**:
   - Generate Form 16 certificates
   - Issue certificates to employees
   - Track certificate status

### Bulk Operations
- **Bulk TDS Calculation**: Calculate TDS for multiple employees
- **Bulk Certificate Generation**: Generate certificates for all employees
- **Quarterly Return Preparation**: Prepare 24Q returns for filing

## Technical Architecture

### Models Structure
```
tds.tax.slab              # Tax slab configuration
├── tds.tax.slab.line     # Individual tax slab lines

tds.section               # TDS deduction sections
├── tds.section.subsection # Sub-sections for detailed categorization

tds.calculation           # Main TDS calculation engine
├── tds.deduction.line    # Employee deduction declarations
├── tds.monthly.breakdown # Monthly TDS breakdown

tds.certificate           # TDS certificates (Form 16)
tds.challan              # TDS challan management
tds.quarterly.return     # Quarterly return (24Q)
```

### Calculation Logic
The system follows Indian Income Tax calculation methodology:

1. **Gross Total Income** = Salary + Other Income + Previous Employer Income
2. **Taxable Income** = Gross Income - Standard Deduction - Section Deductions
3. **Tax Calculation** = Progressive tax as per applicable slab
4. **Rebate Application** = Section 87A rebate if applicable
5. **Surcharge Calculation** = Based on total income brackets
6. **Education Cess** = 4% on (Tax + Surcharge)
7. **Total Tax Liability** = Tax + Surcharge + Cess

### Key Features from hr_contract_extension Analysis
Based on the reference module analysis, this system incorporates:

- **Complex Computed Fields**: Efficient dependency management for real-time calculations
- **HTML Rendering**: Rich tax breakdown displays with formatted tables
- **Financial Year Handling**: Proper April-March financial year support
- **Validation Constraints**: Data integrity checks at model level
- **Wizard-based Operations**: User-friendly bulk operation interfaces
- **Accordion UI**: Organized form layouts for better user experience

## Security

### Access Control
- **TDS User**: Can view and manage own TDS calculations
- **TDS Manager**: Full access to all TDS operations and configurations
- **Record Rules**: Employee-specific data access restrictions

### Data Protection
- Sensitive financial data encryption
- Audit logging for all changes
- Role-based access control
- Document attachment security

## Compliance

### Indian Tax Law Compliance
- Follows latest Income Tax Act provisions
- Supports both Old and New tax regimes
- Accurate surcharge and cess calculations
- Proper rebate applications

### Reporting Standards
- Standard Form 16 format
- 24Q return format compliance
- Challan reconciliation reports
- Audit trail reports

## Support

### Documentation
- User manual for HR teams
- Employee self-service guide
- Administrator configuration guide
- API documentation for developers

### Maintenance
- Regular updates for tax law changes
- Performance optimization
- Bug fixes and enhancements
- Migration support for new Odoo versions

## Version History

### v1.0 (Current)
- Initial release with core TDS functionality
- Support for 2024-25 tax slabs
- Employee self-service portal
- Basic reporting and compliance features

## License

This module is licensed under OEEL-1 (Odoo Enterprise Edition License).

## Credits

Developed based on analysis of the `hr_contract_extension` module patterns and Indian TDS requirements.
