# KPT Stock Item Ledger

## Overview
A comprehensive stock item ledger report for Odoo 17 that provides detailed tracking of inventory movements with running balances, similar to accounting ledgers.

## Features

### Modern Accounting-Style Report Interface
- **Professional UI**: Matches Odoo's standard accounting ledger views
- **Date Range Filters**: Built-in date filtering (today, this week, this month, this quarter, this year, custom)
- **Product Selection**: Easy product selection via dedicated "Select Product" button
- **Multi-Company Support**: Company selector for multi-company environments
- **Export Options**: PDF and XLSX export capabilities

### Comprehensive Stock Tracking
- **Opening Balance**: Shows stock quantity and value at the start of the period
- **Movement Details**: 
  - Date of movement
  - Document reference (picking name)
  - Partner (vendor/customer)
  - In Quantity & Value
  - Out Quantity & Value
  - Running Balance (Qty & Value)
- **Closing Balance**: Final stock position at end of period

### Intelligent Valuation
The module uses multiple sources to determine stock values:
1. **Stock Valuation Layers** (for automated costing products)
2. **Purchase Order Lines** (for PO-linked receipts)
3. **Stock Move Price Unit**
4. **Vendor Bill Lines** (for bill-first workflows via kpt_purchase_extension)

### Works with All Products
- Uses `stock.move` records (state=done)
- Works regardless of costing method (FIFO, AVCO, Standard)
- Supports both stockable and consumable products

## Installation

1. Ensure dependencies are installed:
   - `stock`
   - `stock_account`
   - `account`

2. Install the module:
   ```bash
   python odoo-bin -c odoo.conf -d YOUR_DB -i kpt_stock_item_ledger
   ```

## Usage

### Accessing the Report
**Location**: Inventory → Reporting → Stock Item Ledger

### Steps to View Ledger
1. Open the Stock Item Ledger report
2. Select date range using the date filter
3. Click "Select Product" button
4. Choose a product from the dropdown
5. Click "Apply"
6. View the detailed ledger with opening balance, movements, and closing balance

### Understanding the Report

#### Columns
- **Date**: Transaction date
- **Document**: Reference (e.g., WH/IN/00001)
- **Partner**: Vendor or customer involved
- **In Qty**: Quantity received into stock
- **In Value**: Value of goods received
- **Out Qty**: Quantity issued from stock
- **Out Value**: Value of goods issued
- **Balance Qty**: Running quantity balance
- **Balance Value**: Running value balance

#### Report Structure
```
Product Name [Product Code]
├── Opening Balance: Shows starting position
├── Movement 1: First transaction in period
├── Movement 2: Second transaction
├── ...
└── Closing Balance: Final position (highlighted)
```

### Filters Available
- **Date Range**: Predefined periods or custom date range
- **Company**: Select company (multi-company setups)
- **Product**: Via "Select Product" button

### Export Options
- **PDF**: Print-ready format
- **XLSX**: Excel spreadsheet for further analysis

## Technical Details

### Models

#### `kpt.stock.item.ledger.report.handler`
- Custom report handler extending `account.report.custom.handler`
- Implements dynamic line generation
- Handles product selection and data computation

#### `stock.item.ledger.product.wizard`
- Transient model for product selection
- Provides user-friendly product picker

#### `stock.item.ledger.wizard` (Legacy)
- Original wizard-based approach
- Kept for backward compatibility
- Hidden from menu by default

### Data Flow
1. User selects product via wizard
2. Report handler retrieves all done stock moves for the product
3. Moves are categorized as incoming/outgoing based on location types
4. Opening balance calculated from moves before date range
5. Period movements processed chronologically
6. Running balances computed for each movement
7. Closing balance calculated and displayed

### Location Logic
- **Internal Locations**: `usage='internal'`
- **Incoming**: From non-internal → internal location
- **Outgoing**: From internal → non-internal location
- **Internal Transfers**: Counted based on destination location

## Integration with Other Modules

### kpt_purchase_extension
When installed alongside `kpt_purchase_extension`, the ledger can retrieve vendor bill prices for receipts created from bills, providing accurate valuation even in bill-first workflows.

### Standard Odoo Modules
- **Purchase**: Retrieves PO line prices
- **Stock Account**: Uses valuation layers for automated costing
- **Account**: Integrates with accounting reports menu

## Version History

### 17.0.1.0.1 (Current)
- Fixed data not showing issue
- Added "Select Product" button for easy product selection
- Improved UI to match Odoo standard ledger views
- Added proper date range filters
- Moved menu to Inventory → Reporting
- Enhanced report styling with proper level classes
- Added product code display in header
- Improved opening/closing balance presentation

### 17.0.1.0.0 (Initial)
- Basic stock item ledger functionality
- Wizard-based product selection
- Opening and closing balance calculation

## Troubleshooting

### No Data Showing
- Ensure you've clicked "Select Product" and chosen a product
- Verify the product has stock movements in the selected date range
- Check that movements are in "done" state

### Incorrect Values
- Verify product costing method is set correctly
- Check if valuation layers exist (for automated costing)
- Ensure purchase orders or vendor bills have correct prices

### Performance Issues
- Use shorter date ranges for products with many movements
- Consider archiving old stock moves if database is large

## License
LGPL-3

## Support
For issues or questions, contact KPT support team.
