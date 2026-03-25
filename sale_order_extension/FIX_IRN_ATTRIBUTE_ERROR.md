# Fix: AttributeError - 'account.move' object has no attribute 'irn'

## Problem

When printing Tax Invoice reports, the system threw an AttributeError:
```
AttributeError: 'account.move' object has no attribute 'irn'
Template: sale_order_extension.report_invoice_document1
Path: /t/t[1]/table[2]
Node: <table style="width: 100%; border-collapse: collapse;" t-if="doc.irn"/>
```

## Root Cause

The `irn` field (Invoice Reference Number for e-Invoicing) is defined in the `einvoice_addons` module, not in `sale_order_extension`. The template `kpt_tax_invoice.xml` was referencing `doc.irn` directly in a `t-if` condition, which caused an AttributeError when the `einvoice_addons` module was not installed or the field didn't exist.

### Fields from einvoice_addons module:
- `irn` - Invoice Reference Number
- `ack_no` - Acknowledgment Number
- `ack_date` - Acknowledgment Date
- `e_qr_code` - E-Invoice QR Code
- `signed_qr` - Signed QR Code
- `e_barcode` - E-Invoice Barcode

## Solution Applied

Changed the template condition from:
```xml
<table style="width: 100%; border-collapse: collapse;" t-if="doc.irn">
```

To:
```xml
<table style="width: 100%; border-collapse: collapse;" t-if="hasattr(doc, 'irn') and doc.irn">
```

This change was applied to **all 3 occurrences** in the template (Original, Duplicate, and Triplicate copies).

## Files Modified

- `d:\odoo\odoo-17.0\Kpt_dev_17\kpt_addons\sale_order_extension\views\kpt_tax_invoice.xml`
  - Line 116: Original invoice section
  - Line 470: Duplicate invoice section
  - Line 824: Triplicate invoice section

## How It Works

The `hasattr(doc, 'irn')` function checks if the `irn` attribute exists on the `doc` object before trying to access it. This prevents the AttributeError when:

1. The `einvoice_addons` module is not installed
2. The invoice doesn't have e-invoice data yet
3. The field is not available for any other reason

All related fields (`ack_no`, `ack_date`, `e_qr_code`) are inside the protected table block, so they're also safe from AttributeError.

## Upgrade Instructions

**Update the module:**
```bash
python odoo-bin -c odoo.conf -d YOUR_DATABASE -u sale_order_extension --stop-after-init
```

Or restart Odoo server to reload the views:
```bash
# Stop Odoo
# Start Odoo
python odoo-bin -c odoo.conf
```

## Testing

1. **Without einvoice_addons installed:**
   - Print a Tax Invoice
   - Verify it prints successfully without the e-Invoice section
   - No AttributeError should occur

2. **With einvoice_addons installed:**
   - Print a Tax Invoice for an invoice with e-Invoice data
   - Verify the e-Invoice section appears with IRN, Ack No, Ack Date, and QR code
   - Print a Tax Invoice for an invoice without e-Invoice data
   - Verify it prints successfully without the e-Invoice section

## Alternative Solutions (Not Implemented)

### Option 1: Add einvoice_addons as dependency
Add `'einvoice_addons'` to the `depends` list in `__manifest__.py`. This would make the field always available but would force installation of einvoice_addons even if not needed.

**Not recommended** because:
- Forces dependency on a module that may not be needed
- Less flexible for deployments without e-invoicing

### Option 2: Add irn field to sale_order_extension
Define the `irn` field in `sale_order_extension/models/account_move.py`. This would duplicate the field definition.

**Not recommended** because:
- Violates DRY principle
- Can cause conflicts if both modules are installed
- Field definitions should stay in their logical module

## Notes

- The fix is backward compatible
- No database migration required
- Works with or without `einvoice_addons` installed
- Follows Odoo best practices for optional module dependencies
