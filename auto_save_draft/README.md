# Auto Save Sales Orders

Automatically saves draft records in Odoo to prevent data loss from unsaved work.

## Supported Models

- **Sale Orders** (`sale.order`)

## Features

- ✅ Saves when a customer is first entered to create a valid record
- ✅ Saves every 4 minutes thereafter if changes detected
- ✅ Only saves when all required fields are filled
- ✅ Only operates on draft state records
- ✅ Prevents data loss from unsaved work
- ✅ No configuration required

## Installation

1. Download or clone this module into your Odoo addons directory
2. Update the apps list in Odoo (Settings → Apps → Update Apps List)
3. Search for "Auto Save Sales Orders" and install

## Requirements

- Odoo 18.0
- Dependencies: `base`, `web`, `sale_management`

## How It Works

The module patches Odoo's `FormController` to add automatic saving functionality:

1. When you open a draft sale order a timer starts
2. After 4 minutes, if changes are detected and required fields are filled, the record saves automatically
3. Subsequent saves occur every 4 minutes if changes are detected
4. The timer resets when you manually save

## License

LGPL-3

## Author

**ProFast Supply**

## Support

For issues or feature requests, please contact us through our website or open an issue on GitHub.
