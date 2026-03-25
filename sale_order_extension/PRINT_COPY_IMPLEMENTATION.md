# Print Copy Selection Implementation

## Overview
This implementation adds a print copy selection feature to all reports in the `sale_order_extension` module. Users can select to print 1, 2, or 3 copies with labels: Original, Duplicate, and Triplicate.

## Features Implemented

### 1. Print Copy Wizard (`wizard/print_copy_wizard.py`)
- Transient model that prompts users to select number of copies
- Options: 1 (Original), 2 (Original + Duplicate), 3 (Original + Duplicate + Triplicate)
- Passes `num_copies` context to report generation

### 2. Model Extensions
Created print helper methods for each model:
- **`models/sale_order_print.py`**: Methods for Sale Order reports
  - `action_print_quotation_copies()`
  - `action_print_proforma_copies()`
  - `action_print_proforma_dispatch_copies()`

- **`models/stock_picking_print.py`**: Methods for Stock Picking reports
  - `action_print_delivery_challan_copies()`
  - `action_print_delivery_note_copies()`
  - `action_print_delivery_note_sample_copies()`

- **`models/purchase_order_print.py`**: Methods for Purchase Order reports
  - `action_print_purchase_order_copies()`

- **`models/account_move_print.py`**: Methods for Account Move reports
  - `action_print_tax_invoice_copies()`

### 3. UI Buttons (`views/print_buttons.xml`)
Added print buttons to form views:
- Sale Order form: Print Quotation, Print Pro-Forma, Print Pro-Forma (Dispatch)
- Stock Picking form: Print Delivery Challan, Print Delivery Note, Print Delivery Note (Sample)
- Purchase Order form: Print Purchase Order
- Account Move form: Print Tax Invoice

### 4. Report Template Updates
Modified report templates to support dynamic copy generation:

**Pattern used:**
```xml
<template id="report_name">
    <t t-call="web.html_container">
        <t t-set="num_copies" t-value="num_copies or 1"/>
        <t t-set="copy_labels" t-value="['Original', 'Duplicate', 'Triplicate']"/>
        
        <t t-foreach="docs" t-as="doc">
            <t t-foreach="range(num_copies)" t-as="copy_index">
                <t t-set="copy_label" t-value="copy_labels[copy_index]"/>
                <t t-call="module.report_document_template" t-lang="doc.partner_id.lang"/>
                <!-- Page break between copies -->
                <div t-if="copy_index &lt; num_copies - 1" style="page-break-after: always;"/>
            </t>
        </t>
    </t>
</template>
```

**Copy Label Display:**
```xml
<strong>(<t t-esc="copy_label or 'Original'"/>)</strong>
```

### 5. Reports Updated
- ✅ Delivery Challan (`delivery_challan.xml`)
- ⏳ Delivery Note (`delivery_note.xml`)
- ⏳ Delivery Slip (`delivery_slip_template.xml`)
- ⏳ Sale Quotation (`kpt_sale_quotation_template.xml`)
- ⏳ Pro-Forma Invoice (`kpt_pro_forma_invoice.xml`)
- ⏳ Pro-Forma Dispatch (`pro_forma_dispatch_team.xml`)
- ⏳ Purchase Order (`kpt_purchase_order_template.xml`)
- ⏳ Tax Invoice (`kpt_tax_invoice.xml`)

## Usage

### For Users:
1. Open any supported document (Sale Order, Stock Picking, Purchase Order, Invoice)
2. Click the appropriate print button (e.g., "Print Delivery Challan")
3. Select number of copies in the wizard:
   - **Original**: Prints 1 copy with "Original" label
   - **Original + Duplicate**: Prints 2 copies with "Original" and "Duplicate" labels
   - **Original + Duplicate + Triplicate**: Prints 3 copies with all three labels
4. Click "Print" to generate the PDF

### For Developers:
To add print copy support to a new report:

1. **Create print method in model:**
```python
def action_print_report_copies(self):
    return self.action_print_with_copies('module.report_action_xml_id')
```

2. **Add button to view:**
```xml
<button name="action_print_report_copies" 
        string="Print Report" 
        type="object" 
        class="btn-primary"/>
```

3. **Update report template:**
```xml
<template id="report_main">
    <t t-call="web.html_container">
        <t t-set="num_copies" t-value="num_copies or 1"/>
        <t t-set="copy_labels" t-value="['Original', 'Duplicate', 'Triplicate']"/>
        
        <t t-foreach="docs" t-as="doc">
            <t t-foreach="range(num_copies)" t-as="copy_index">
                <t t-set="copy_label" t-value="copy_labels[copy_index]"/>
                <t t-call="module.report_document"/>
                <div t-if="copy_index &lt; num_copies - 1" style="page-break-after: always;"/>
            </t>
        </t>
    </t>
</template>
```

4. **Add copy label to document template:**
```xml
<strong>(<t t-esc="copy_label or 'Original'"/>)</strong>
```

## Files Modified/Created

### New Files:
- `wizard/print_copy_wizard.py`
- `wizard/print_copy_wizard.xml`
- `models/sale_order_print.py`
- `models/stock_picking_print.py`
- `models/purchase_order_print.py`
- `models/account_move_print.py`
- `views/print_buttons.xml`

### Modified Files:
- `__manifest__.py` - Added new data files
- `models/__init__.py` - Added new model imports
- `wizard/__init__.py` - Added wizard import
- `security/ir.model.access.csv` - Added wizard access rights
- `views/delivery_challan.xml` - Updated for dynamic copies

## Installation
1. Update the module: `odoo-bin -u sale_order_extension -d your_database`
2. The print buttons will appear automatically in the respective forms
3. Old report menu items remain available for backward compatibility

## Technical Notes
- The wizard uses a transient model (`models.TransientModel`)
- Context variable `num_copies` is passed to report rendering
- Page breaks ensure each copy starts on a new page
- Copy labels are displayed in red color (#F7374F) for visibility
- Removed hardcoded duplicate/triplicate sections from templates
