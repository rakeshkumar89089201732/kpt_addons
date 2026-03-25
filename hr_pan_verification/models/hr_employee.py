import re
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    pan_verified_name = fields.Char(string='PAN Verified Name', readonly=True, copy=False)
    pan_verification_status = fields.Selection(
        [
            ('not_verified', 'Not Verified'),
            ('verified', 'Verified'),
            ('failed', 'Failed'),
        ],
        string='PAN Verification Status',
        default='not_verified',
        readonly=True,
        copy=False,
    )
    pan_active_status = fields.Selection(
        [
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('cancelled', 'Cancelled'),
            ('deactivated', 'Deactivated'),
            ('unknown', 'Unknown'),
        ],
        string='PAN Active Status',
        readonly=True,
        copy=False,
        help='Active status of PAN in government database',
    )
    pan_holder_type = fields.Selection(
        [
            ('individual', 'Individual'),
            ('company', 'Company'),
            ('huf', 'Hindu Undivided Family'),
            ('firm', 'Firm/Partnership'),
            ('aop', 'Association of Persons'),
            ('trust', 'Trust'),
            ('boi', 'Body of Individuals'),
            ('local_authority', 'Local Authority'),
            ('juridical_person', 'Artificial Juridical Person'),
            ('government', 'Government'),
        ],
        string='PAN Holder Type',
        readonly=True,
        copy=False,
        help='Type of PAN holder as per government records',
    )
    pan_last_verified = fields.Datetime(string='PAN Last Verified On', readonly=True, copy=False)
    pan_verification_raw = fields.Text(string='PAN Verification Raw Response', readonly=True, copy=False)
    pan_verification_message = fields.Char(string='Verification Message', readonly=True, copy=False)
    pan_verification_method = fields.Selection(
        [
            ('offline', 'Offline (Format Check)'),
            ('api', 'API (Government Database)'),
        ],
        string='Verification Method',
        readonly=True,
        copy=False,
    )

    @api.model
    def _validate_pan_format(self, pan):
        """Validate PAN format: 5 letters, 4 digits, 1 letter (e.g., ABCDE1234F)"""
        if not pan:
            return False, _('PAN number is required')
        
        pan = pan.strip().upper()
        
        if len(pan) != 10:
            return False, _('PAN must be exactly 10 characters')
        
        # PAN format: AAAAA9999A
        # First 5 characters: Alphabets
        # Next 4 characters: Numbers
        # Last character: Alphabet
        pan_pattern = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')
        
        if not pan_pattern.match(pan):
            return False, _('Invalid PAN format. Expected format: ABCDE1234F (5 letters, 4 digits, 1 letter)')
        
        return True, pan

    def _verify_pan_offline(self, pan):
        """Offline PAN validation without API call"""
        is_valid_format, result = self._validate_pan_format(pan)
        if not is_valid_format:
            return {
                'valid': False,
                'message': result,
                'pan': pan,
            }
        
        pan = result  # Normalized PAN
        
        # Extract holder type from PAN structure
        holder_code_map = {
            'P': 'individual',
            'C': 'company',
            'H': 'huf',
            'F': 'firm',
            'A': 'aop',
            'T': 'trust',
            'B': 'boi',
            'L': 'local_authority',
            'J': 'juridical_person',
            'G': 'government',
        }
        
        holder_type_display = {
            'individual': 'Individual',
            'company': 'Company',
            'huf': 'Hindu Undivided Family (HUF)',
            'firm': 'Firm/Partnership',
            'aop': 'Association of Persons (AOP)',
            'trust': 'Trust',
            'boi': 'Body of Individuals (BOI)',
            'local_authority': 'Local Authority',
            'juridical_person': 'Artificial Juridical Person',
            'government': 'Government',
        }
        
        holder_type = holder_code_map.get(pan[3], False)
        holder_display = holder_type_display.get(holder_type, 'Unknown')
        
        return {
            'valid': True,
            'pan': pan,
            'message': _('Valid PAN format for %s (Offline validation - Format check only)', holder_display),
            'holder_type': holder_type,
            'active_status': 'unknown',  # Cannot determine from offline validation
        }

    def action_verify_pan(self):
        """Verify PAN via external API or offline validation"""
        for emp in self:
            pan = emp.pan_number
            if not pan:
                raise UserError(_('Please set PAN Number first.'))
            
            # Validate PAN format first
            is_valid_format, result = self._validate_pan_format(pan)
            if not is_valid_format:
                raise ValidationError(result)
            
            pan = result  # Use normalized PAN (uppercase, trimmed)
            
            # Check validation mode
            use_offline = self.env['ir.config_parameter'].sudo().get_param(
                'hr_pan_verification.use_offline_validation', 'False'
            )
            
            if str(use_offline).lower() in ('1', 'true', 'yes'):
                # Offline validation mode
                try:
                    res = self._verify_pan_offline(pan)
                    valid = bool(res.get('valid'))
                    message = res.get('message', '')
                    holder_type = res.get('holder_type', False)
                    active_status = res.get('active_status', 'unknown')
                    
                    vals = {
                        'pan_number': pan,
                        'pan_verification_status': 'verified' if valid else 'failed',
                        'pan_last_verified': fields.Datetime.now(),
                        'pan_verification_message': message,
                        'pan_verification_raw': _('Offline validation - Format check only'),
                        'pan_verification_method': 'offline',
                        'pan_holder_type': holder_type,
                        'pan_active_status': active_status,
                    }
                    
                    emp.write(vals)
                    
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('PAN Verified (Offline)'),
                            'message': message,
                            'type': 'success' if valid else 'warning',
                            'sticky': False,
                        }
                    }
                except Exception as e:
                    emp.write({
                        'pan_verification_status': 'failed',
                        'pan_verification_message': str(e),
                        'pan_last_verified': fields.Datetime.now(),
                        'pan_verification_method': 'offline',
                    })
                    raise UserError(_('PAN validation failed: %s', str(e)))
            else:
                # API validation mode - Full government database verification
                try:
                    res = self.env['hr.pan.verification.client'].verify_pan(pan)
                    valid = bool(res.get('valid'))
                    name = res.get('name') or False
                    active_status = res.get('active_status', 'unknown')
                    holder_type = res.get('holder_type', False)
                    message = res.get('message') or (
                        _('PAN verified successfully') if valid else _('PAN verification failed')
                    )
                    
                    vals = {
                        'pan_number': pan,
                        'pan_verified_name': name,
                        'pan_verification_status': 'verified' if valid else 'failed',
                        'pan_last_verified': fields.Datetime.now(),
                        'pan_verification_raw': res.get('raw') or False,
                        'pan_verification_message': message,
                        'pan_verification_method': 'api',
                        'pan_active_status': active_status,
                        'pan_holder_type': holder_type,
                    }
                    
                    # Auto-fill employee name if not set or matches PAN
                    if name and (not emp.name or emp.name.strip() == emp.pan_number.strip()):
                        vals['name'] = name
                    
                    emp.write(vals)
                    
                    # Build detailed notification message
                    notification_parts = [_('PAN %s verified successfully', pan)]
                    if name:
                        notification_parts.append(_('Name: %s', name))
                    if active_status and active_status != 'unknown':
                        status_display = dict(emp._fields['pan_active_status'].selection).get(active_status, active_status)
                        notification_parts.append(_('Status: %s', status_display))
                    if holder_type:
                        type_display = dict(emp._fields['pan_holder_type'].selection).get(holder_type, holder_type)
                        notification_parts.append(_('Type: %s', type_display))
                    
                    notification_message = ' | '.join(notification_parts)
                    
                    # Show success notification
                    if valid:
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _('PAN Verified (Government Database)'),
                                'message': notification_message,
                                'type': 'success',
                                'sticky': True,  # Keep visible for important info
                            }
                        }
                    else:
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _('Verification Failed'),
                                'message': message or _('PAN verification failed'),
                                'type': 'warning',
                                'sticky': False,
                            }
                        }
                except UserError as e:
                    emp.write({
                        'pan_verification_status': 'failed',
                        'pan_verification_message': str(e),
                        'pan_last_verified': fields.Datetime.now(),
                        'pan_verification_method': 'api',
                    })
                    raise
                except Exception as e:
                    emp.write({
                        'pan_verification_status': 'failed',
                        'pan_verification_message': _('Verification error: %s', str(e)),
                        'pan_last_verified': fields.Datetime.now(),
                        'pan_verification_method': 'api',
                    })
                    raise UserError(_('PAN verification failed: %s', str(e)))
        
        return True

    @api.onchange('pan_number')
    def _onchange_pan_number_auto_verify(self):
        """Auto-verify PAN when changed (if enabled) and validate format"""
        for emp in self:
            if not emp.pan_number:
                # Clear verification status when PAN is removed
                emp.pan_verification_status = 'not_verified'
                emp.pan_verified_name = False
                emp.pan_verification_message = False
                continue
            
            # Normalize PAN (uppercase, trim)
            pan = emp.pan_number.strip().upper()
            emp.pan_number = pan
            
            # Validate format
            is_valid_format, result = self._validate_pan_format(pan)
            if not is_valid_format:
                emp.pan_verification_status = 'not_verified'
                emp.pan_verification_message = result
                return {
                    'warning': {
                        'title': _('Invalid PAN Format'),
                        'message': result,
                    }
                }
            
            # Check if auto-verify is enabled
            auto_verify = self.env['ir.config_parameter'].sudo().get_param('hr_pan_verification.auto_verify')
            if str(auto_verify).lower() not in ('1', 'true', 'yes'):
                emp.pan_verification_status = 'not_verified'
                emp.pan_verification_message = _('Click "Verify PAN" to verify')
                return
            
            # Auto-verify if PAN is 10 characters and format is valid
            if len(pan) == 10:
                try:
                    # Reset status before verification
                    emp.pan_verification_status = 'not_verified'
                    emp.pan_verification_message = _('Verifying...')
                    # Note: In onchange, we can't call action_verify_pan directly
                    # as it requires saved record. Show message instead.
                    return {
                        'warning': {
                            'title': _('PAN Verification'),
                            'message': _('Save the record to auto-verify PAN, or click "Verify PAN" button.'),
                        }
                    }
                except Exception as e:
                    emp.pan_verification_status = 'failed'
                    emp.pan_verification_message = str(e)
    
    @api.constrains('pan_number')
    def _check_pan_format(self):
        """Validate PAN format on save"""
        for emp in self:
            if emp.pan_number:
                is_valid, message = self._validate_pan_format(emp.pan_number)
                if not is_valid:
                    raise ValidationError(message)
