# Employee Entry and Exit - Dynamic Offer Letter System

## Overview
This module provides comprehensive employee lifecycle management with a **dynamic offer letter template system** that allows you to configure job position-specific templates with roles, responsibilities, and terms.

## Key Features

### 1. **Dynamic Offer Letter Templates**
- Configure templates for each job position
- Define roles & responsibilities per position
- Set work location, hours, probation period, and notice period
- Add benefits, perks, and position-specific terms
- Templates auto-populate when creating offers

### 2. **Menu Structure**
- **Payroll > Employee Offers**: Create and manage offer letters
- **Payroll > Configuration > Offer Letter Templates**: Configure templates

### 3. **Template Placeholders**
Use these placeholders in template content for dynamic replacement:
- `[CANDIDATE_NAME]` - Candidate's name
- `[POSITION]` - Job position name
- `[DEPARTMENT]` - Department name
- `[COMPANY]` - Company name
- `[JOINING_DATE]` - Formatted joining date
- `[OFFER_DATE]` - Formatted offer date

## How to Use

### Step 1: Configure Templates
1. Go to **Payroll > Configuration > Offer Letter Templates**
2. Click **Create**
3. Fill in:
   - **Template Name**: e.g., "Software Developer Template"
   - **Job Position**: Select the position this template applies to
   - **Introduction**: Welcome message with placeholders
   - **Roles & Responsibilities**: Define key duties
   - **Work Details**: Location, hours, probation, notice period
   - **Benefits & Perks**: List all benefits
   - **Terms & Conditions**: General and specific terms
   - **Closing**: Closing paragraph

### Step 2: Create Offer Letter
1. Go to **Payroll > Employee Offers**
2. Click **Create**
3. Fill in candidate details
4. Select **Job Position** - template will auto-populate
5. Select **Offer Letter Template** (auto-selected based on position)
6. Review and customize the auto-populated content
7. Fill in salary details
8. Send the offer

### Step 3: Generate PDF
- Click **Print Offer Letter** to generate a professional PDF
- The PDF includes all dynamic content with placeholders replaced

## Template Configuration Fields

### Basic Information
- **Template Name**: Descriptive name for the template
- **Job Position**: Associated job position (one template per position)
- **Sequence**: Display order
- **Active**: Enable/disable template

### Content Sections
1. **Introduction**: Opening paragraph
2. **Roles & Responsibilities**: Key duties and responsibilities
3. **Work Details**:
   - Work Location
   - Work Hours
   - Probation Period (months)
   - Notice Period (days)
   - Reporting Structure
4. **Benefits & Perks**: List of benefits
5. **Additional Terms**: Position-specific terms
6. **General Terms & Conditions**: Standard terms
7. **Closing**: Closing paragraph

## Workflow

```
Configure Template → Create Offer → Template Auto-Populates → 
Customize if Needed → Send Offer → Accept → Create Employee & Contract
```

## Security

- **Users**: Can read templates, create/edit offers
- **HR Managers**: Full access to templates and offers

## Technical Details

### Models
- `offer.letter.template`: Template configuration
- `employee.offer`: Offer letter with template integration

### Key Methods
- `_onchange_position_id()`: Auto-select template when position changes
- `_onchange_template_id()`: Populate offer content from template
- `_replace_placeholders()`: Replace template placeholders with actual values
- `get_processed_content()`: Get field content with placeholders replaced

### Constraints
- One template per job position per company
- Probation and notice periods must be non-negative
- Joining date must be after offer date

## Example Template

**Introduction:**
```html
<p>We are pleased to offer you the position of <strong>[POSITION]</strong> in our <strong>[DEPARTMENT]</strong> department.</p>
<p>We believe your skills will be valuable to [COMPANY].</p>
```

**Roles & Responsibilities:**
```html
<ul>
<li>Develop and maintain software applications</li>
<li>Collaborate with cross-functional teams</li>
<li>Write clean, maintainable code</li>
<li>Participate in code reviews</li>
</ul>
```

## Benefits

✅ **Consistency**: Standardized offer letters per position  
✅ **Efficiency**: Auto-population saves time  
✅ **Flexibility**: Customize per candidate while maintaining standards  
✅ **Professional**: Clean, well-formatted PDF output  
✅ **Dynamic**: Placeholders ensure accurate information  

## Upgrade from Previous Version

If upgrading from a version without templates:
1. Install/upgrade the module
2. Create templates for your job positions
3. Existing offers will continue to work
4. New offers will use the template system
