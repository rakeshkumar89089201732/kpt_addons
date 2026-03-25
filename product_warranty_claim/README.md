# Product Warranty and Claim Module

## Overview
This module provides comprehensive warranty management for products in Odoo, including warranty registration, claims, renewals, and history tracking.

## Features

### 1. Warranty Registration
- Generate warranties automatically from sales orders
- Manual warranty creation
- Support for serial number tracking
- Link warranties to sale orders and order lines

### 2. Warranty Types
- **Free Warranty**: No charge for warranty coverage
- **Paid Warranty**: Warranty with associated cost

### 3. Warranty Configuration
- Product-level warranty settings
- Configurable warranty period (in months)
- Warranty price for paid warranties
- Enable/disable warranty per product

### 4. Warranty Claims
- Create claims for warranty issues
- Track claim status (Draft, Submitted, In Progress, Resolved, Rejected)
- Claim types: Repair, Replacement, Refund, Other
- Check if claim is within warranty period
- Assign claims to users
- Track claim costs

### 5. Warranty Renewals
- Renew expired or expiring warranties
- Create new warranty records from renewals
- Support for both free and paid renewals
- Automatic invoice generation for paid renewals

### 6. Warranty History
- Complete warranty lifecycle tracking
- View all claims and renewals for a warranty
- Track warranty status (Draft, Active, Expired, Cancelled)

### 7. Invoice Integration
- Automatic invoice creation for paid warranties (configurable)
- Manual invoice creation option
- Link invoices to warranties and renewals

## Installation
1. Copy the module to your Odoo addons directory
2. Update the apps list
3. Install "Product Warranty and Claim"

## Configuration
1. Go to **Settings** → **Warranty Settings**
2. Enable "Auto-create Invoice for Paid Warranties" if you want automatic invoice generation

## Usage

### Setting up Product Warranty
1. Go to **Inventory** → **Products** → Select a product
2. In the product form, configure:
   - **Has Warranty**: Enable warranty for this product
   - **Warranty Type**: Choose Free or Paid
   - **Warranty Period**: Set period in months
   - **Warranty Price**: Set price if Paid warranty

### Creating Warranties from Sales Orders
1. Confirm a sale order with products that have warranty enabled
2. Click **"Create Warranties"** button
3. Warranties will be automatically created for eligible products

### Creating Warranty Claims
1. Go to **Sales** → **Warranty** → **Claims**
2. Click **Create**
3. Select the warranty
4. Fill in claim details and submit

### Renewing Warranties
1. Go to **Sales** → **Warranty** → **Renewals**
2. Click **Create**
3. Select the warranty to renew
4. Set renewal period and dates
5. Confirm and complete the renewal

## Technical Details
- Models: `product.warranty`, `product.warranty.claim`, `product.warranty.renewal`
- Dependencies: `sale`, `sale_management`, `stock`, `account`
- Security: User and Manager groups with appropriate access rights

## Support
For issues or questions, contact your system administrator.
