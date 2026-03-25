# KPT Multi-Currency Performa Invoice

## Overview
This module extends Odoo's Sale Order functionality to provide enhanced multi-currency support for performa invoices and quotations.

## Features
- **Automatic Currency Selection**: When you select a customer, the currency is automatically set based on:
  - Customer's pricelist currency (first priority)
  - Customer's currency field (second priority)
  - Company's default currency (fallback)

- **Manual Currency Override**: You can manually change the currency in the sale order form even after customer selection

- **Automatic Price Recalculation**: When currency is changed, all product prices are automatically recalculated based on:
  - Pricelist rules
  - Currency conversion rates
  - Current exchange rates

- **Invoice Integration**: Selected currency is automatically carried forward to invoices

- **Enhanced Views**:
  - Currency field visible in sale order form (after pricelist field)
  - Currency column in sale order tree/list view
  - Currency grouping option in search filters

## Installation
1. Copy the module to your Odoo addons directory
2. Update the apps list
3. Install "KPT Multi-Currency Performa Invoice" from Apps menu

## Usage
1. Go to Sales > Orders > Quotations or Sales > Orders > Orders
2. Create a new sale order
3. Select a customer - currency will be set automatically
4. (Optional) Change the currency manually if needed
5. Add products - prices will be calculated in selected currency
6. Confirm and create invoice - currency will be maintained

## Technical Details
- **Module Name**: kpt_multi_currency
- **Version**: 17.0.1.0.0
- **Depends**: sale_management, account
- **License**: LGPL-3

## Models Extended
- `sale.order`: Added currency_id field with enhanced functionality
- `sale.order.line`: Enhanced price calculation based on currency

## Configuration
No additional configuration required. The module works out of the box with Odoo's existing:
- Currency settings (Accounting > Configuration > Currencies)
- Pricelist configuration (Sales > Configuration > Pricelists)
- Customer currency settings (Contacts > Customer > Accounting tab)

## Notes
- Ensure currencies are properly configured with exchange rates
- Pricelists can have different currencies assigned
- Currency conversion uses the exchange rate valid on the sale order date
