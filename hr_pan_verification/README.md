# HR PAN Verification Module

## Overview

This module provides automatic PAN (Permanent Account Number) verification for employees in Odoo 17. It integrates with external PAN verification APIs to validate employee PAN numbers and auto-fill employee details.

## Features

### 1. **PAN Format Validation**
- Validates PAN format before API calls
- Expected format: `ABCDE1234F` (5 letters, 4 digits, 1 letter)
- Auto-converts PAN to uppercase
- Shows instant validation errors

### 2. **API Integration**
- Supports RapidAPI PAN verification services
- Compatible with multiple providers:
  - pan-card-verification-at-lowest-price
  - pan-no-details
- Configurable API endpoint, host, and key

### 3. **Verification Workflow**

#### Manual Verification
1. Enter PAN number in employee form
2. Click "Verify PAN" button
3. System validates format and calls API
4. Results displayed with status badge

#### Auto Verification (Optional)
1. Enable "Auto-Verify PAN on Change" in Settings
2. Enter PAN number
3. System validates format automatically
4. Save record to trigger API verification

### 4. **Visual Status Indicators**
- **Not Verified** (Gray badge): PAN not yet verified
- **Verified** (Green badge): PAN successfully verified
- **Failed** (Red badge): Verification failed

### 5. **Auto-Fill Employee Details**
- Automatically fills employee name from verified PAN data
- Only updates if name is empty or matches PAN number
- Stores verified name separately for reference

## Configuration

### 1. Install the Module
```bash
python odoo-bin -c odoo.conf -d YOUR_DATABASE -i hr_pan_verification --stop-after-init
```

### 2. Configure API Settings
Navigate to: **Settings > Human Resources > HR PAN Verification**

Configure the following:
- **API URL**: Full API endpoint URL
- **API Host**: RapidAPI host (e.g., `pan-card-verification.p.rapidapi.com`)
- **API Key**: Your RapidAPI key
- **Auto-Verify PAN**: Enable/disable automatic verification on PAN change
- **Allow Employee Creation**: Allow creating employees from contract form

### 3. Example Configuration

**For pan-card-verification-at-lowest-price provider:**
```
API URL: https://pan-card-verification-at-lowest-price.p.rapidapi.com/verification
API Host: pan-card-verification-at-lowest-price.p.rapidapi.com
API Key: your_rapidapi_key_here
```

**For pan-no-details provider:**
```
API URL: https://pan-no-details.p.rapidapi.com/pan
API Host: pan-no-details.p.rapidapi.com
API Key: your_rapidapi_key_here
```

## Usage

### Employee Form

1. **Navigate to Employee**
   - Go to Employees > Employees
   - Open or create an employee record

2. **Enter PAN Number**
   - Enter PAN in format: `ABCDE1234F`
   - System auto-converts to uppercase
   - Format validation happens instantly

3. **Verify PAN**
   - Click "Verify PAN" button
   - Wait for API response
   - Check verification status badge

4. **Review Results**
   - **Verification Status**: Shows current status
   - **Verification Message**: Shows success/error message
   - **Verified Name**: Name retrieved from PAN database
   - **Last Verified**: Timestamp of last verification

### Contract Form (Optional)

If "Allow Employee Creation" is enabled:
- Enter PAN in contract form
- System can create employee from PAN verification data

## Fields Added to Employee

| Field | Type | Description |
|-------|------|-------------|
| `pan_verification_status` | Selection | Verification status (not_verified/verified/failed) |
| `pan_verified_name` | Char | Name retrieved from PAN verification |
| `pan_verification_message` | Char | Success/error message from verification |
| `pan_last_verified` | Datetime | Timestamp of last verification attempt |
| `pan_verification_raw` | Text | Raw API response (for debugging) |

## Validation Rules

### PAN Format Validation
- **Length**: Exactly 10 characters
- **Pattern**: `[A-Z]{5}[0-9]{4}[A-Z]`
- **Example**: `ABCDE1234F`

### Validation Triggers
1. **On Change**: Instant format validation
2. **On Save**: Format validation constraint
3. **On Verify**: Format + API validation

## Error Handling

### Common Errors

**Invalid PAN Format**
```
Error: Invalid PAN format. Expected format: ABCDE1234F (5 letters, 4 digits, 1 letter)
Solution: Enter PAN in correct format
```

**API Not Configured**
```
Error: PAN verification is not configured. Please set API URL/Host/Key in Settings.
Solution: Configure API settings in Settings > HR > HR PAN Verification
```

**API Request Failed**
```
Error: PAN verification request failed: [error details]
Solution: Check API credentials, network connectivity, and API quota
```

**Verification Failed**
```
Status: Failed
Message: PAN verification failed
Solution: Verify PAN number is correct and active
```

## API Response Handling

The module automatically extracts data from various API response formats:

### Supported Response Patterns
```json
{
  "valid": true,
  "name": "JOHN DOE",
  "pan_status": "VALID"
}
```

```json
{
  "data": {
    "full_name": "JOHN DOE",
    "valid": true
  }
}
```

```json
{
  "first_name": "JOHN",
  "last_name": "DOE",
  "is_valid": true
}
```

## Security

- API key stored in system parameters (encrypted)
- Only users with HR access can verify PAN
- Verification history stored for audit trail
- Raw API responses stored for debugging

## Dependencies

- `hr` - Odoo HR module
- `hr_contract` - HR Contract module
- `hr_contract_extension` - Custom HR contract extensions

## Technical Details

### Models Extended
- `hr.employee` - Employee PAN verification
- `hr.contract` - Contract PAN verification (optional)
- `res.config.settings` - API configuration

### New Models
- `hr.pan.verification.client` - Abstract model for API client

### Methods

**`action_verify_pan()`**
- Validates PAN format
- Calls external API
- Updates verification status
- Shows notification

**`_validate_pan_format(pan)`**
- Validates PAN format using regex
- Returns (is_valid, result/message)

**`_onchange_pan_number_auto_verify()`**
- Triggered on PAN change
- Validates format
- Shows warnings for invalid format
- Triggers auto-verification if enabled

## Troubleshooting

### PAN Not Verifying Automatically
1. Check if "Auto-Verify PAN on Change" is enabled in Settings
2. Ensure PAN format is correct (10 characters, valid pattern)
3. Save the record after entering PAN

### API Errors
1. Verify API credentials in Settings
2. Check RapidAPI subscription status
3. Verify API quota not exceeded
4. Check network connectivity

### Format Validation Errors
1. Ensure PAN is exactly 10 characters
2. Use format: 5 letters + 4 digits + 1 letter
3. System auto-converts to uppercase

## Support

For issues or questions:
1. Check error message in "Verification Message" field
2. Review raw API response in "PAN Verification Raw Response" field
3. Check Odoo logs for detailed error traces

## Changelog

### Version 17.0.1.0.0
- Initial release
- PAN format validation
- API integration with RapidAPI
- Auto-verification support
- Visual status indicators
- Enhanced error handling
- User notifications
