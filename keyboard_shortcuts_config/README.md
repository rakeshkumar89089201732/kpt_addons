# Keyboard Shortcuts Configuration Module

## Overview

This module allows users and administrators to configure custom keyboard shortcuts in Odoo 17. You can create shortcuts at both individual user level and globally for all users.

## Features

### Core Features
- **User-Level Shortcuts**: Create personal shortcuts that only affect your account
- **Global Shortcuts**: Administrators can create shortcuts for all users
- **Context-Aware**: Shortcuts can be configured to work only in specific views (form, list, kanban, etc.)
- **Model-Specific**: Optionally restrict shortcuts to specific models
- **Conflict Detection**: Automatic detection and warning of conflicting shortcuts
- **Import/Export**: Backup and share your shortcut configurations

### Pre-configured Shortcuts
The module comes with these default global shortcuts:
- **Enter**: Move to next field (in forms)
- **Ctrl+Enter**: Insert new line in text fields
- **Ctrl+S**: Save current record
- **Ctrl+N**: Create new record
- **Ctrl+E**: Edit current record
- **Ctrl+D**: Duplicate current record
- **Ctrl+F**: Focus on search (in list views)
- **Escape**: Close dialog/modal

### Available Actions
- **Navigation**: Next field, previous field, first field, close dialog, search focus
- **Form Actions**: Save, discard, edit record
- **Text Input**: New line, tab indent
- **Record Actions**: Create, delete, duplicate

## Installation

1. Copy the module to your addons directory:
   ```
   d:\odoo\odoo-17.0\Kpt_dev_17\kpt_addons\keyboard_shortcuts_config\
   ```

2. Update the apps list in Odoo

3. Install the "Keyboard Shortcuts Configuration" module

4. The module will automatically load with default shortcuts

## Usage

### For Users

#### View Your Shortcuts
1. Go to **Keyboard Shortcuts > My Shortcuts**
2. See all shortcuts available to you (personal + global)

#### Create Personal Shortcut
1. Go to **Keyboard Shortcuts > My Shortcuts**
2. Click **Create**
3. Fill in:
   - **Name**: Descriptive name (e.g., "Quick Save")
   - **Key Code**: The key to press (e.g., "s", "Enter", "F1")
   - **Modifier Keys**: Check Ctrl, Alt, Shift, or Meta as needed
   - **Action**: Select what the shortcut should do
   - **Apply On**: Choose which view type (form, list, all, etc.)
4. Click **Save**

#### Import/Export Shortcuts
1. Go to **Keyboard Shortcuts > Configuration > Import/Export**
2. Choose **Export** to backup your shortcuts
3. Choose **Import** to restore or load shortcuts from a file

#### Manage in User Preferences
1. Go to **Preferences** (top-right menu)
2. Navigate to **Keyboard Shortcuts** tab
3. Enable/disable shortcuts or view your personal shortcuts
4. Use **Reset to Defaults** to remove all personal shortcuts

### For Administrators

#### Create Global Shortcuts
1. Go to **Keyboard Shortcuts > Configuration > All Shortcuts**
2. Click **Create**
3. Set **Scope** to **Global (All Users)**
4. Configure the shortcut as needed
5. All users will immediately have access to this shortcut

#### Manage Actions
1. Go to **Keyboard Shortcuts > Configuration > Shortcut Actions**
2. View all available actions
3. Create custom actions if needed (requires JavaScript knowledge)

#### Security Groups
- **Keyboard Shortcuts User**: Can view and create personal shortcuts
- **Keyboard Shortcuts Manager**: Can manage all shortcuts and create global ones

## Configuration Examples

### Example 1: Enter for Next Field
```
Name: Enter - Next Field
Key Code: Enter
Modifiers: None
Action: Next Field
Scope: Global
Apply On: Form View
```

### Example 2: Ctrl+Enter for New Line
```
Name: Ctrl+Enter - New Line
Key Code: Enter
Modifiers: Ctrl
Action: New Line
Scope: Global
Apply On: Form View
```

### Example 3: Custom Save Shortcut
```
Name: Alt+S - Save
Key Code: s
Modifiers: Alt
Action: Save Record
Scope: User
Apply On: Form View
```

## Technical Details

### Models
- `keyboard.shortcut`: Main shortcut configuration
- `shortcut.action`: Action definitions
- `res.users`: Extended with shortcut preferences

### JavaScript Services
- `shortcut_manager`: Main service that handles keyboard events
- Automatically loads user shortcuts on login
- Executes actions based on shortcut configuration

### API Methods
- `get_shortcuts_for_user(user_id)`: Get all shortcuts for a user
- `get_user_shortcuts_json()`: JSON API for JavaScript

## Troubleshooting

### Shortcut Not Working
1. Check if the shortcut is **Active**
2. Verify you're in the correct **View Type** (form, list, etc.)
3. Check for **Conflicts** with other shortcuts
4. Ensure **Enable Keyboard Shortcuts** is checked in your preferences
5. Refresh your browser to reload shortcuts

### Conflicts
- The system automatically detects conflicting shortcuts
- Conflicting shortcuts are marked with a warning
- View conflicts by clicking the **View Conflicts** button
- Resolve by disabling one of the conflicting shortcuts or changing the key combination

### Browser Default Actions
- Some shortcuts may conflict with browser defaults (e.g., Ctrl+S)
- The module prevents default actions when configured
- If a shortcut doesn't work, try a different key combination

## Customization

### Adding Custom Actions
To add custom JavaScript actions:

1. Create a new action in **Shortcut Actions**
2. Set **Action Type** to **Custom JavaScript**
3. Set **Action Code** to a unique identifier
4. Extend `shortcut_manager.js` to handle your custom action code

### Context-Specific Shortcuts
You can make shortcuts work only in specific contexts:
- **Apply On**: Select specific view types
- **Specific Models**: Choose which models the shortcut applies to
- Leave empty for universal shortcuts

## Support

For issues or feature requests, contact your system administrator.

## Credits

- **Author**: KPT
- **Version**: 17.0.1.0.0
- **License**: LGPL-3
