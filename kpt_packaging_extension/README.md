# KPT Packaging Extension

## Overview

This module extends Odoo 17.0's standard product packaging functionality to add detailed weight and packaging information for products that require precise weight tracking per piece and per packaging unit.

## Features

- **Weight per Piece (Wt./Pcs)**: Track the weight of individual pieces/units
- **Pieces per Packaging (PCS/Bag)**: Define how many pieces are contained in each packaging unit
- **Packaging Weight**: Record the weight of empty packaging material (bag, box, etc.)
- **Average Weight per Packaging (AVG Wt./Bag)**: Automatically calculated field showing total weight including packaging

## Use Case

This module is particularly useful for products like:
- Couplings
- Fasteners
- Small components sold in bulk packaging
- Any product where weight per piece and packaging weight need to be tracked separately

## Installation

1. Copy the `kpt_packaging_extension` folder to your Odoo addons directory
2. Update the apps list in Odoo
3. Install the module from Apps menu

## Usage

### Adding Packaging Information to Products

1. Go to **Inventory > Products > Products**
2. Open a product
3. Navigate to the **Inventory** tab
4. In the **Packaging** section, add or edit packaging
5. Fill in the new fields:
   - **Weight per Piece**: Enter the weight of one individual piece
   - **Pieces per Packaging**: Enter how many pieces are in this packaging
   - **Packaging Weight**: Enter the weight of the empty packaging material
   - **Avg Weight per Packaging**: This is automatically calculated

### Example

For a coupling product (KPT C-0001):
- Weight per Piece: 0.012 kg
- Pieces per Packaging: 1200 pieces
- Packaging Weight: 0.20 kg
- Avg Weight per Packaging: (0.012 × 1200) + 0.20 = 14.60 kg

## Technical Details

### Dependencies
- `product`: Odoo standard product module
- `stock`: Odoo standard inventory module

### Models Extended
- `product.packaging`: Added fields for weight tracking

### New Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `weight_per_piece` | Float | Weight of one individual piece/unit |
| `pieces_per_packaging` | Integer | Number of pieces in this packaging |
| `packaging_weight` | Float | Weight of empty packaging material |
| `avg_weight_per_packaging` | Float (Computed) | Total weight = (weight_per_piece × pieces_per_packaging) + packaging_weight |

### Views Modified
- Product Packaging Form View
- Product Packaging Tree View
- Product Template Form View (Packaging section)

## Version

- **Module Version**: 17.0.1.0.0
- **Odoo Version**: 17.0
- **License**: LGPL-3

## Author

KPT

## Support

For issues or questions, please contact your system administrator.
