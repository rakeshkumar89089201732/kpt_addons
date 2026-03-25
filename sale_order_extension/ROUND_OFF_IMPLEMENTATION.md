# Round-Off Implementation in Sale Order Extension

## Overview
Added editable round-off functionality to Sale Orders and Invoices that:
- Auto-calculates round-off to make totals round numbers
- Allows manual editing of round-off amount
- Shows in the view (visible in totals section)
- Integrates with accounting journals for proper financial reporting

## Features Implemented

### 1. Sale Order Round-Off
**Location:** `models/sale_order.py`

**Fields Added:**
- `round_off_amount` - Editable monetary field that auto-calculates but can be manually adjusted
- `amount_total_rounded` - Final total including round-off

**Behavior:**
- Auto-calculates round-off to nearest integer when amount_total changes
- Preserves manual edits (doesn't overwrite user changes)
- Transfers to invoice when creating invoice from sale order

**View:** `views/sale_order_view.xml`
- Round-off field appears after amount_total in totals section
- Editable when order is in draft/sent state
- Shows final rounded total with separator line

### 2. Invoice/Bill Round-Off
**Location:** `models/account_move.py`

**Fields Added:**
- `round_off_amount` - Editable round-off amount
- `round_off_account_id` - Account for posting round-off entries
- `amount_total_rounded` - Final total with round-off

**Accounting Integration:**
- Automatically creates journal entry line for round-off amount
- Uses configured round-off account from company settings
- Falls back to searching for accounts with "round" in code
- Creates proper debit/credit entries based on invoice type

**View:** `views/account_move_view.xml`
- Round-off fields in invoice totals section
- Editable in draft state only

### 3. Company Configuration
**Location:** `models/res_company.py`, `models/res_config_settings.py`

**Configuration:**
- Added `round_off_account_id` to company settings
- Accessible via Accounting → Configuration → Settings
- Allows selection of income_other or expense account for round-off

**View:** `views/res_config_settings_view.xml`
- Round-off account selector in Accounting Settings
- Clear description of purpose

## How It Works

### Auto-Calculation Logic
```python
@api.depends('amount_total')
def _compute_round_off_amount(self):
    for order in self:
        # Only auto-calculate if not manually set
        if not order._origin.round_off_amount:
            rounded_total = round(order.amount_total)
            order.round_off_amount = rounded_total - order.amount_total
```

### Manual Override
- User can click on round-off field and edit the value
- Once edited, auto-calculation won't override the manual value
- To reset to auto-calculated value, clear the field

### Accounting Entry
When invoice is posted, the round-off creates a journal entry line:
- **Debit/Credit:** Based on round-off amount (positive/negative)
- **Account:** From company round-off account configuration
- **Description:** "Round Off"

## Usage Instructions

### Setup (One-time)
1. Go to **Accounting → Configuration → Settings**
2. Find "Round Off Account" section
3. Select an account (create if needed):
   - For sales: Income account (e.g., "Miscellaneous Income")
   - For purchases: Expense account (e.g., "Miscellaneous Expense")
4. Save settings

### In Sale Orders
1. Create/edit a sale order
2. Add products and see the total (e.g., ₹29,502.36)
3. **Round-off auto-calculates** (e.g., -₹2.36 to make it ₹29,500.00)
4. **Rounded Total shows** ₹29,500.00
5. **Optional:** Edit round-off manually if needed
6. Confirm order and create invoice
7. Round-off transfers to invoice automatically

### In Invoices
1. Open invoice (created from SO or manually)
2. Round-off field shows in totals
3. Edit if needed (in draft state)
4. Post invoice
5. **Journal entry includes round-off line** with configured account

## Example Scenario

**Sale Order:**
- Untaxed Amount: ₹25,002.00
- IGST 18%: ₹4,500.36
- **Total:** ₹29,502.36
- **Round Off:** -₹2.36 (auto-calculated)
- **Rounded Total:** ₹29,500.00

**Invoice Journal Entry:**
```
Debit: Customer (Accounts Receivable)     ₹29,500.00
Credit: Sales                              ₹25,002.00
Credit: IGST Payable                       ₹4,500.36
Debit: Round Off (Misc. Income)            ₹2.36
```

## Files Modified/Created

### Models
- `models/sale_order.py` - Added round-off fields and logic
- `models/account_move.py` - Added round-off with journal integration
- `models/res_company.py` - Added round-off account configuration
- `models/res_config_settings.py` - Settings UI for round-off account
- `models/__init__.py` - Added new model imports

### Views
- `views/sale_order_view.xml` - Added round-off fields to SO form
- `views/account_move_view.xml` - Added round-off fields to invoice form
- `views/res_config_settings_view.xml` - Configuration UI

### Manifest
- `__manifest__.py` - Added new view files to data list

## Testing Checklist

- [ ] Create sale order with decimal total
- [ ] Verify round-off auto-calculates
- [ ] Edit round-off manually and verify it persists
- [ ] Confirm order and create invoice
- [ ] Verify round-off transfers to invoice
- [ ] Configure round-off account in settings
- [ ] Post invoice and check journal entries
- [ ] Verify round-off line appears with correct account
- [ ] Check reports show correct rounded totals
- [ ] Test with different invoice types (customer/vendor)

## Upgrade Instructions

```bash
# Upgrade the module
python odoo-bin -c odoo.conf -d YOUR_DATABASE -u sale_order_extension
```

After upgrade:
1. Configure round-off account in Accounting Settings
2. Test with a new sale order
3. Verify journal entries in posted invoices
