# KPT Purchase Extension

## Overview
This module extends the purchase and inventory functionality in Odoo 17 to provide bidirectional integration between vendor bills and inventory receipts.

## Features

### 1. Create Vendor Bill from Receipt
- **Location**: Inventory > Operations > Receipts
- **Button**: "Create Bill" (visible on validated incoming receipts)
- **Functionality**: 
  - Creates a vendor bill with all products from the receipt
  - Pre-fills product quantities and unit prices
  - Links the bill to the receipt automatically

### 2. Auto-Create Receipt from Bill
- **Location**: Accounting > Vendors > Bills
- **Trigger**: Automatically when posting a vendor bill
- **Functionality**:
  - If no receipt is linked, creates a new receipt automatically
  - Validates the receipt with all bill line items
  - Links the receipt to the bill

### 3. View Linked Receipt from Bill
- **Location**: Vendor Bill form view
- **Button**: "View Receipt" smart button (visible when receipt exists)
- **Fields**:
  - `receipt_id`: Manually linked receipt
  - `auto_created_receipt_id`: Auto-generated receipt
  - Smart button shows either linked or auto-created receipt

### 4. View Linked Bills from Receipt
- **Location**: Receipt form view
- **Button**: "Bills" smart button with count
- **Functionality**: Shows all vendor bills created from this receipt

## Technical Details

### Models Extended

#### `stock.picking`
- **New Fields**:
  - `vendor_bill_ids`: One2many to account.move
  - `vendor_bill_count`: Computed field for smart button
- **New Methods**:
  - `action_create_vendor_bill()`: Creates bill from receipt
  - `action_view_vendor_bills()`: Opens linked bills
  - `_prepare_vendor_bill_values()`: Prepares bill data

#### `account.move`
- **New Fields**:
  - `receipt_id`: Many2one to stock.picking (manual link)
  - `auto_created_receipt_id`: Many2one to stock.picking (auto-created)
  - `has_receipt`: Computed boolean
- **Extended Methods**:
  - `action_post()`: Auto-creates receipt if needed
- **New Methods**:
  - `_create_receipt_from_bill()`: Creates and validates receipt
  - `action_view_receipt()`: Opens linked receipt

## Installation

1. Copy the module to your addons path
2. Update the apps list
3. Install "KPT Purchase Extension"

## Dependencies
- `purchase`
- `stock`
- `account`

## Usage Scenarios

### Scenario 1: Receipt First, Then Bill
1. Receive products in Inventory
2. Validate the receipt
3. Click "Create Bill" button
4. Bill is created with receipt data
5. Edit and post the bill

### Scenario 2: Bill First, Then Receipt
1. Create vendor bill in Accounting
2. Add bill lines with products
3. Post the bill
4. Receipt is automatically created and validated
5. View receipt using "View Receipt" button

## Version
- **Module Version**: 17.0.1.0.0
- **Odoo Version**: 17.0

## License
LGPL-3
