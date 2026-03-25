# KPT Stock Ledger Module

## Overview
This module provides a comprehensive stock ledger report that tracks product movements with inward/outward quantities and values, similar to traditional accounting ledgers.

## Features

### Stock Ledger Report
- **Product-wise tracking**: Generate ledger for any product
- **Date range filtering**: Specify from/to dates for the report
- **Opening Balance**: Automatically calculates opening stock and value
- **Inwards/Outwards**: Tracks all incoming and outgoing stock movements
- **Closing Balance**: Running balance with quantity and value
- **Voucher Details**: Shows voucher type, number, and partner information

### Supported Voucher Types
- Opening Balance
- Sales
- Purchase
- Sales Return
- Purchase Return
- Stock Journal
- Manufacturing
- Inventory Adjustment
- Internal Transfer
- Delivery Order
- Receipt

### Key Fields
- **Date**: Transaction date
- **Particulars**: Partner name or description
- **Vch Type**: Type of transaction
- **Vch No**: Document/Voucher number
- **Inwards**: Quantity, Value, and Rate
- **Outwards**: Quantity, Value, and Rate
- **Closing**: Quantity, Value, and Rate

## Usage

### Generate Stock Ledger
1. Go to **Inventory > Stock Ledger > Generate Stock Ledger**
2. Select the product
3. Choose date range (From Date to To Date)
4. Optionally select a specific location
5. Click **Generate Ledger**

### View Stock Ledger
- Navigate to **Inventory > Stock Ledger > Stock Ledger**
- Use filters to search by product, partner, voucher type, or date
- Group by product, partner, voucher type, or date

### From Product Form
- Open any product form
- Click **Action > Generate Stock Ledger** (available in the action menu)

## Technical Details

### Models
- `stock.ledger`: Main ledger model storing all transactions
- `stock.ledger.wizard`: Wizard for generating ledger reports
- `stock.move`: Inherited to auto-create ledger entries

### Auto-Creation
- Ledger entries are automatically created when stock moves are validated
- Only moves involving internal locations are tracked
- Valuation is calculated from stock valuation layers

### Calculations
- **Opening Balance**: Sum of all moves before the from_date
- **Inward**: Stock coming into internal locations
- **Outward**: Stock going out of internal locations
- **Closing**: Running balance (Opening + Inward - Outward)
- **Rate**: Value divided by quantity

## Installation
1. Copy the module to your addons directory
2. Update the apps list
3. Install "KPT Stock Ledger"

## Dependencies
- stock
- stock_account
- sale_stock
- purchase_stock

## Configuration
No special configuration required. The module works out of the box with standard Odoo stock operations.

## Notes
- Only products with real-time valuation are tracked
- Ledger entries are read-only (cannot be manually created/edited)
- Use the wizard to regenerate ledger for any date range
- Multi-company support included

## Version
17.0.1.0.0

## Author
KPT

## License
LGPL-3
