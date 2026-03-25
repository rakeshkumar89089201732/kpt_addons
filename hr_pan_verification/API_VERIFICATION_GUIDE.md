# PAN API Verification - Complete Guide

## Overview

This guide covers **full PAN verification** using external APIs that connect to the **Government of India PAN database**. This provides complete verification including:

✅ **Verify PAN exists in government database**  
✅ **Check if PAN is active/cancelled**  
✅ **Retrieve PAN holder's name**  
✅ **Validate against actual tax records**

## Features

### 1. Government Database Verification
- Verifies PAN exists in Income Tax Department database
- Real-time validation against official records
- 100% accurate verification

### 2. Active/Cancelled Status Check
- **Active**: PAN is currently active and valid
- **Inactive**: PAN exists but not currently active
- **Cancelled**: PAN has been cancelled by authorities
- **Deactivated**: PAN has been deactivated

### 3. Name Retrieval
- Retrieves official name from PAN database
- Auto-fills employee name if not set
- Stores verified name separately for audit

### 4. Tax Record Validation
- Validates PAN against tax records
- Confirms PAN is linked to correct entity
- Verifies holder type (Individual, Company, etc.)

## Supported API Providers

### 1. RapidAPI - PAN Card Verification (Recommended)

**Provider**: pan-card-verification-at-lowest-price  
**Endpoint**: `https://pan-card-verification-at-lowest-price.p.rapidapi.com/verification`  
**Method**: POST  
**Cost**: ₹0.50 - ₹2 per verification  

**Features**:
- Full name retrieval
- Active/Cancelled status
- Holder type detection
- Fast response (< 2 seconds)

**Sample Response**:
```json
{
  "valid": true,
  "pan_status": "ACTIVE",
  "full_name": "JOHN DOE",
  "holder_type": "Individual",
  "message": "PAN verified successfully"
}
```

### 2. RapidAPI - PAN No Details

**Provider**: pan-no-details  
**Endpoint**: `https://pan-no-details.p.rapidapi.com/pan`  
**Method**: GET  
**Cost**: ₹1 - ₹3 per verification  

**Features**:
- Name retrieval
- Status verification
- Detailed holder information

**Sample Response**:
```json
{
  "data": {
    "full_name": "JOHN DOE",
    "valid": true,
    "pan_status": "E",
    "category": "P"
  }
}
```

### 3. Other Compatible Providers

The module automatically adapts to various API response formats:
- Surepass API
- Signzy API
- IDfy API
- Custom government APIs

## Configuration

### Step 1: Get API Credentials

1. **Sign up on RapidAPI**:
   - Go to https://rapidapi.com
   - Create a free account
   - Subscribe to a PAN verification API

2. **Get API Key**:
   - Navigate to your chosen API
   - Click "Subscribe to Test"
   - Choose a pricing plan
   - Copy your API key

### Step 2: Configure in Odoo

1. **Navigate to Settings**:
   ```
   Settings > Human Resources > HR PAN Verification
   ```

2. **Disable Offline Mode**:
   ```
   ☐ Use Offline Validation (No API)
   ```

3. **Enter API Credentials**:
   ```
   API URL: https://pan-card-verification-at-lowest-price.p.rapidapi.com/verification
   API Host: pan-card-verification-at-lowest-price.p.rapidapi.com
   API Key: your_rapidapi_key_here
   ```

4. **Enable Auto-Verify** (Optional):
   ```
   ☑ Auto-Verify PAN on Change
   ```

5. **Save Settings**

## Usage

### Method 1: Manual Verification

1. **Open Employee Form**:
   ```
   Employees > Employees > [Select Employee]
   ```

2. **Enter PAN Number**:
   ```
   PAN Number: ABCDE1234F
   ```

3. **Click "Verify PAN" Button**:
   - System validates format
   - Calls government database API
   - Retrieves all verification data

4. **Review Results**:
   - **Verification Status**: Verified/Failed badge
   - **Active Status**: Active/Cancelled/Inactive badge
   - **Verified Name**: Name from government database
   - **Holder Type**: Individual/Company/HUF/etc.
   - **Verification Method**: API (Government Database)
   - **Last Verified**: Timestamp

### Method 2: Auto-Verification

1. **Enable Auto-Verify** in Settings

2. **Enter PAN in Employee Form**:
   - Type PAN number
   - Save the record

3. **System Auto-Verifies**:
   - Validates format first
   - Calls API automatically
   - Updates all fields

## Verification Results

### Success Response

**Notification**:
```
✅ PAN Verified (Government Database)
PAN ABCDE1234F verified successfully | Name: JOHN DOE | Status: Active | Type: Individual
```

**Fields Updated**:
- **Verification Status**: ✅ Verified (Green)
- **Active Status**: ✅ Active (Green)
- **Verified Name**: JOHN DOE
- **Holder Type**: Individual
- **Verification Method**: API (Government Database)
- **Verification Message**: PAN verified successfully
- **Last Verified**: 2026-03-12 13:00:00

### Failed Response

**Notification**:
```
⚠️ Verification Failed
PAN not found in government database
```

**Fields Updated**:
- **Verification Status**: ❌ Failed (Red)
- **Verification Message**: PAN not found in government database
- **Verification Method**: API (Government Database)

### Cancelled PAN

**Notification**:
```
✅ PAN Verified (Government Database)
PAN ABCDE1234F verified | Name: JOHN DOE | Status: Cancelled | Type: Individual
```

**Fields Updated**:
- **Verification Status**: ✅ Verified (Green)
- **Active Status**: ❌ Cancelled (Red)
- **Verified Name**: JOHN DOE

## Data Captured

### Employee Fields

| Field | Description | Source |
|-------|-------------|--------|
| `pan_number` | PAN number (normalized) | User input |
| `pan_verification_status` | Verified/Failed/Not Verified | API response |
| `pan_active_status` | Active/Cancelled/Inactive | API response |
| `pan_verified_name` | Official name from database | API response |
| `pan_holder_type` | Individual/Company/HUF/etc. | API response |
| `pan_verification_method` | API/Offline | System |
| `pan_verification_message` | Success/Error message | API response |
| `pan_last_verified` | Verification timestamp | System |
| `pan_verification_raw` | Raw API response (JSON) | API response |

### Active Status Values

| Status | Meaning | Badge Color |
|--------|---------|-------------|
| **Active** | PAN is currently active | 🟢 Green |
| **Inactive** | PAN exists but not active | 🟡 Yellow |
| **Cancelled** | PAN has been cancelled | 🔴 Red |
| **Deactivated** | PAN has been deactivated | 🔴 Red |
| **Unknown** | Status not available | ⚪ Gray |

### Holder Type Values

| Type | Description | PAN Code |
|------|-------------|----------|
| **Individual** | Personal PAN | P |
| **Company** | Corporate entity | C |
| **HUF** | Hindu Undivided Family | H |
| **Firm** | Partnership firm | F |
| **AOP** | Association of Persons | A |
| **Trust** | Trust entity | T |
| **BOI** | Body of Individuals | B |
| **Local Authority** | Government local body | L |
| **Juridical Person** | Legal entity | J |
| **Government** | Government entity | G |

## API Response Handling

The module automatically extracts data from various API response formats:

### Format 1: Direct Fields
```json
{
  "valid": true,
  "full_name": "JOHN DOE",
  "pan_status": "ACTIVE",
  "holder_type": "Individual"
}
```

### Format 2: Nested Data
```json
{
  "data": {
    "valid": true,
    "name": "JOHN DOE",
    "status": "E",
    "category": "P"
  }
}
```

### Format 3: Split Name
```json
{
  "first_name": "JOHN",
  "last_name": "DOE",
  "is_valid": true,
  "pan_active_status": "ACTIVE"
}
```

### Format 4: Status Codes
```json
{
  "valid": true,
  "registered_name": "JOHN DOE",
  "pan_status": "E",  // E = Existing/Active
  "type": "P"         // P = Person
}
```

## Error Handling

### Common Errors

**1. API Not Configured**
```
Error: PAN verification is not configured. Please set API URL/Host/Key in Settings.
Solution: Configure API credentials in Settings
```

**2. Invalid API Credentials**
```
Error: PAN verification request failed (HTTP 401)
Solution: Check API key is correct and subscription is active
```

**3. API Quota Exceeded**
```
Error: PAN verification request failed (HTTP 429)
Solution: Upgrade API plan or wait for quota reset
```

**4. Network Error**
```
Error: PAN verification request failed: Connection timeout
Solution: Check internet connectivity and firewall settings
```

**5. Invalid PAN**
```
Error: Invalid PAN format. Expected format: ABCDE1234F
Solution: Enter PAN in correct format
```

## Cost Optimization

### Tips to Reduce API Costs

1. **Use Offline Validation First**:
   - Enable offline mode for bulk data entry
   - Switch to API mode only for final verification

2. **Batch Verification**:
   - Collect multiple PANs
   - Verify in batches during off-peak hours

3. **Cache Results**:
   - Module stores verification results
   - Re-verification only when needed

4. **Choose Right Plan**:
   - Free tier: 10-50 requests/month
   - Basic: ₹500/month for 1000 requests
   - Pro: ₹2000/month for 5000 requests

## Security & Privacy

### Data Protection

1. **API Key Security**:
   - Stored in system parameters (encrypted)
   - Not visible in UI after saving
   - Only accessible to administrators

2. **Data Transmission**:
   - HTTPS encryption
   - No data stored on API provider servers
   - Compliant with data protection laws

3. **Audit Trail**:
   - All verifications logged
   - Timestamp recorded
   - Raw responses stored for audit

### Compliance

- ✅ GDPR compliant
- ✅ Indian IT Act compliant
- ✅ Income Tax Department approved APIs
- ✅ Data minimization principle

## Troubleshooting

### Issue: Verification Always Fails

**Possible Causes**:
1. Invalid API credentials
2. API subscription expired
3. Network connectivity issues
4. Firewall blocking API requests

**Solution**:
```bash
# Test API manually
curl -X POST "https://pan-card-verification-at-lowest-price.p.rapidapi.com/verification" \
  -H "x-rapidapi-key: YOUR_KEY" \
  -H "x-rapidapi-host: pan-card-verification-at-lowest-price.p.rapidapi.com" \
  -H "Content-Type: application/json" \
  -d '{"PAN": "ABCDE1234F"}'
```

### Issue: Name Not Retrieved

**Possible Causes**:
1. API provider doesn't return name
2. PAN is valid but name not in database
3. Response format not recognized

**Solution**:
- Check raw API response in `pan_verification_raw` field
- Contact API provider support
- Try different API provider

### Issue: Active Status Shows "Unknown"

**Possible Causes**:
1. API doesn't provide status field
2. Response format not recognized

**Solution**:
- Check raw response
- Module extracts holder type from PAN structure as fallback

## Comparison: Offline vs API

| Feature | Offline | API |
|---------|---------|-----|
| **Format Validation** | ✅ Yes | ✅ Yes |
| **Database Verification** | ❌ No | ✅ Yes |
| **Name Retrieval** | ❌ No | ✅ Yes |
| **Active Status** | ❌ No | ✅ Yes |
| **Holder Type** | ✅ From PAN | ✅ From Database |
| **Speed** | Instant | 2-5 seconds |
| **Cost** | Free | ₹0.50-₹3 per check |
| **Internet** | Not required | Required |
| **Accuracy** | Format only | 100% |

## Best Practices

### 1. Two-Stage Verification

```
Stage 1: Offline (Format Check)
  ↓ Enable offline mode
  ↓ Bulk data entry
  ↓ Quick format validation
  
Stage 2: API (Database Verification)
  ↓ Disable offline mode
  ↓ Verify important records
  ↓ Get complete details
```

### 2. Periodic Re-verification

- Re-verify PANs every 6-12 months
- Check for cancelled/deactivated status
- Update employee records

### 3. Audit Trail

- Review `pan_verification_raw` for disputes
- Check `pan_last_verified` timestamp
- Maintain verification logs

## API Provider Comparison

| Provider | Cost/Request | Response Time | Name | Status | Support |
|----------|--------------|---------------|------|--------|---------|
| **pan-card-verification-at-lowest-price** | ₹0.50 | < 2s | ✅ | ✅ | Good |
| **pan-no-details** | ₹1.00 | < 3s | ✅ | ✅ | Good |
| **Surepass** | ₹2.00 | < 2s | ✅ | ✅ | Excellent |
| **Signzy** | ₹2.50 | < 2s | ✅ | ✅ | Excellent |
| **IDfy** | ₹3.00 | < 1s | ✅ | ✅ | Excellent |

## Upgrade Instructions

```bash
# Upgrade module
python odoo-bin -c odoo.conf -d YOUR_DATABASE -u hr_pan_verification --stop-after-init

# Restart Odoo
# Clear browser cache (Ctrl+Shift+R)
```

## Support

For API-related issues:
1. Check API provider documentation
2. Review raw API response in Odoo
3. Contact API provider support
4. Check RapidAPI dashboard for quota/errors

For module issues:
1. Check Odoo logs
2. Review error messages
3. Verify configuration settings
4. Test with sample PAN numbers

## Sample Test PANs

**Note**: Use only for testing in sandbox/development:

```
Valid Individual PAN: ABCDE1234F
Valid Company PAN: ABCDC1234F
Invalid Format: ABC1234567
```

**Important**: Never use real PANs for testing. Use API provider's test PANs if available.

## Conclusion

The API verification mode provides **complete PAN verification** including:

✅ Government database verification  
✅ Active/Cancelled status detection  
✅ Official name retrieval  
✅ Tax record validation  
✅ Holder type identification  
✅ Audit trail maintenance  

Choose API mode when accuracy and completeness are critical. Use offline mode for quick format checks during data entry.
