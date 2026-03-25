# Odoo UI Enhancements

## Overview

This module provides generic UI enhancements for Odoo 17.0 to improve the display and alignment of tree view (list view) labels and fields across all modules.

## Issues Fixed

### Tree View Column Headers
- **Label Truncation**: Prevents column headers from being cut off with "..."
- **Uneven Alignment**: Ensures all column headers are properly aligned
- **Spacing Issues**: Adds consistent padding and spacing
- **Word Wrapping**: Allows headers to wrap to multiple lines when needed

### Field Display
- Better vertical alignment for all field types
- Improved readability with proper spacing
- Consistent styling across different view contexts
- Better responsive behavior on smaller screens

### Specific Improvements
- Numeric field headers (weight, qty, price, etc.) properly aligned
- Boolean fields centered correctly
- Many2one fields with proper text overflow handling
- Better hover and selection states
- Improved styling for editable tree views
- Better appearance in modals and notebook pages
- **Drag-and-drop visibility**: Fixed invisible fields when dragging rows to reorder
- **Sortable handle**: Improved visibility and cursor feedback
- **Drop placeholder**: Clear visual indicator of where row will be placed

## Installation

1. Copy the `odoo_ui_enhancements` folder to your Odoo addons directory
2. Update the apps list in Odoo
3. Install the module from Apps menu

## Usage

Once installed, the UI improvements will automatically apply to all tree views throughout Odoo. No configuration needed.

This module is completely generic and works with:
- Standard Odoo modules
- Custom modules
- Third-party modules
- Any Odoo installation (Community or Enterprise)

## Technical Details

### Dependencies
- `web`: Odoo standard web module

### Assets
- `tree_view_fixes.scss`: SCSS file with all CSS improvements

### CSS Improvements Include
- Column header text wrapping and alignment
- Consistent padding and spacing
- Better table layout algorithm
- Responsive design improvements
- Enhanced hover and selection states
- Better support for different field types

## Compatibility

- **Odoo Version**: 17.0
- **Browser Support**: All modern browsers (Chrome, Firefox, Safari, Edge)
- **Responsive**: Works on desktop, tablet, and mobile
- **Works with**: Any Odoo module or custom development

## Version

- **Module Version**: 17.0.1.0.0
- **License**: LGPL-3

## Author

Community

## Support

This is a community module. Feel free to use it in any Odoo installation.
