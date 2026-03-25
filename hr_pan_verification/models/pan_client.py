import json
import urllib.error
import urllib.parse
import urllib.request

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None

from odoo import api, models
from odoo.exceptions import UserError


class HrPanVerificationClient(models.AbstractModel):
    _name = 'hr.pan.verification.client'
    _description = 'HR PAN Verification Client'

    @api.model
    def _get_param(self, key, default=False):
        return self.env['ir.config_parameter'].sudo().get_param(key, default)

    @api.model
    def _extract_name(self, payload):
        if not isinstance(payload, dict):
            return False

        # Common split-name patterns
        first_name = payload.get('first_name') or payload.get('firstname')
        last_name = payload.get('last_name') or payload.get('lastname')
        if isinstance(first_name, str) and first_name.strip() and isinstance(last_name, str) and last_name.strip():
            return f"{first_name.strip()} {last_name.strip()}"

        candidates = [
            ('full_name',),
            ('name',),
            ('registered_name',),
            ('name_pan_card',),
            ('name_provided',),
            ('fullname',),
            ('fullName',),
            ('data', 'name'),
            ('data', 'full_name'),
            ('data', 'registered_name'),
            ('data', 'name_pan_card'),
            ('result', 'name'),
            ('result', 'full_name'),
            ('response', 'name'),
            ('response', 'full_name'),
        ]
        for path in candidates:
            cur = payload
            ok = True
            for key in path:
                if isinstance(cur, dict) and key in cur:
                    cur = cur[key]
                else:
                    ok = False
                    break
            if ok and isinstance(cur, str) and cur.strip():
                return cur.strip()
        return False

    @api.model
    def _extract_valid(self, payload):
        if not isinstance(payload, dict):
            return False

        # Common patterns across providers
        if isinstance(payload.get('valid'), bool):
            return payload['valid']
        if isinstance(payload.get('is_valid'), bool):
            return payload['is_valid']

        # RapidAPI provider often returns pan_status='VALID'
        pan_status = payload.get('pan_status')
        if isinstance(pan_status, str) and pan_status.strip().upper() in ('VALID', 'VERIFIED', 'SUCCESS'):
            return True

        # Nested patterns
        data = payload.get('data')
        if isinstance(data, dict) and isinstance(data.get('valid'), bool):
            return data['valid']

        return False

    @api.model
    def _extract_message(self, payload):
        if not isinstance(payload, dict):
            return False
        msg = payload.get('message')
        if isinstance(msg, str) and msg.strip():
            return msg.strip()
        data = payload.get('data')
        if isinstance(data, dict):
            msg = data.get('message')
            if isinstance(msg, str) and msg.strip():
                return msg.strip()
        return False

    @api.model
    def _extract_active_status(self, payload):
        """Extract PAN active/cancelled status from API response"""
        if not isinstance(payload, dict):
            return 'unknown'

        # Check various status fields
        status_fields = [
            'pan_status', 'status', 'pan_active_status', 'active_status',
            'is_active', 'is_cancelled', 'is_deactivated'
        ]
        
        for field in status_fields:
            value = payload.get(field)
            if isinstance(value, str):
                value_upper = value.strip().upper()
                if value_upper in ('ACTIVE', 'VALID', 'E', 'EXISTING'):
                    return 'active'
                elif value_upper in ('INACTIVE', 'INVALID', 'I'):
                    return 'inactive'
                elif value_upper in ('CANCELLED', 'CANCELED', 'C', 'DEACTIVATED', 'D'):
                    return 'cancelled'
            elif isinstance(value, bool):
                if field in ('is_active',) and value:
                    return 'active'
                elif field in ('is_cancelled', 'is_deactivated') and value:
                    return 'cancelled'

        # Check nested data
        data = payload.get('data')
        if isinstance(data, dict):
            for field in status_fields:
                value = data.get(field)
                if isinstance(value, str):
                    value_upper = value.strip().upper()
                    if value_upper in ('ACTIVE', 'VALID', 'E', 'EXISTING'):
                        return 'active'
                    elif value_upper in ('INACTIVE', 'INVALID', 'I'):
                        return 'inactive'
                    elif value_upper in ('CANCELLED', 'CANCELED', 'C', 'DEACTIVATED', 'D'):
                        return 'cancelled'

        return 'unknown'

    @api.model
    def _extract_holder_type(self, payload, pan):
        """Extract PAN holder type from API response or PAN structure"""
        if not isinstance(payload, dict):
            return self._get_holder_type_from_pan(pan)

        # Try to get from API response
        type_fields = ['holder_type', 'pan_type', 'type', 'entity_type', 'category']
        
        for field in type_fields:
            value = payload.get(field)
            if isinstance(value, str):
                return self._normalize_holder_type(value)

        # Check nested data
        data = payload.get('data')
        if isinstance(data, dict):
            for field in type_fields:
                value = data.get(field)
                if isinstance(value, str):
                    return self._normalize_holder_type(value)

        # Fallback to PAN structure
        return self._get_holder_type_from_pan(pan)

    @api.model
    def _get_holder_type_from_pan(self, pan):
        """Extract holder type from PAN structure (4th character)"""
        if not pan or len(pan) < 4:
            return False

        holder_code = pan[3].upper()
        holder_map = {
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
        return holder_map.get(holder_code, False)

    @api.model
    def _normalize_holder_type(self, type_str):
        """Normalize holder type string to standard values"""
        if not isinstance(type_str, str):
            return False

        type_upper = type_str.strip().upper()
        
        # Mapping of various API response formats to standard types
        type_map = {
            'INDIVIDUAL': 'individual',
            'PERSON': 'individual',
            'P': 'individual',
            'COMPANY': 'company',
            'CORPORATE': 'company',
            'C': 'company',
            'HUF': 'huf',
            'HINDU UNDIVIDED FAMILY': 'huf',
            'H': 'huf',
            'FIRM': 'firm',
            'PARTNERSHIP': 'firm',
            'F': 'firm',
            'AOP': 'aop',
            'ASSOCIATION OF PERSONS': 'aop',
            'A': 'aop',
            'TRUST': 'trust',
            'T': 'trust',
            'BOI': 'boi',
            'BODY OF INDIVIDUALS': 'boi',
            'B': 'boi',
            'LOCAL AUTHORITY': 'local_authority',
            'L': 'local_authority',
            'JURIDICAL PERSON': 'juridical_person',
            'ARTIFICIAL JURIDICAL PERSON': 'juridical_person',
            'J': 'juridical_person',
            'GOVERNMENT': 'government',
            'G': 'government',
        }
        
        return type_map.get(type_upper, False)

    @api.model
    def verify_pan(self, pan):
        pan = (pan or '').strip().upper()
        if not pan:
            raise UserError('Please enter a PAN number.')

        url = self._get_param('hr_pan_verification.api_url')
        host = self._get_param('hr_pan_verification.api_host')
        api_key = self._get_param('hr_pan_verification.api_key')

        if not url or not host or not api_key:
            raise UserError('PAN verification is not configured. Please set API URL/Host/Key in Settings.')

        headers = {
            'x-rapidapi-key': api_key,
            'x-rapidapi-host': host,
        }

        # Provider compatibility:
        # - pan-card-verification-at-lowest-price: POST JSON {"PAN": "..."}
        # - pan-no-details: GET with querystring ?panno=...
        use_get_query = 'pan-no-details.p.rapidapi.com' in (host or '') or 'pan-no-details.p.rapidapi.com' in (url or '')
        if not use_get_query:
            headers['Content-Type'] = 'application/json'

        if requests:
            try:
                if use_get_query:
                    resp = requests.get(url, headers=headers, params={'panno': pan}, timeout=20)
                else:
                    resp = requests.post(url, json={'PAN': pan}, headers=headers, timeout=20)
            except Exception as e:
                raise UserError(f'PAN verification request failed: {e}')

            content_type = (resp.headers.get('Content-Type') or '').lower()
            body_text = resp.text
            status_code = resp.status_code
        else:
            if use_get_query:
                url_with_qs = url
                qs = urllib.parse.urlencode({'panno': pan})
                if '?' in (url_with_qs or ''):
                    url_with_qs = f"{url_with_qs}&{qs}"
                else:
                    url_with_qs = f"{url_with_qs}?{qs}"
                req = urllib.request.Request(
                    url_with_qs,
                    headers=headers,
                    method='GET',
                )
            else:
                req = urllib.request.Request(
                    url,
                    data=json.dumps({'PAN': pan}).encode('utf-8'),
                    headers=headers,
                    method='POST',
                )
            try:
                with urllib.request.urlopen(req, timeout=20) as response:
                    status_code = response.status
                    content_type = (response.headers.get('Content-Type') or '').lower()
                    body_text = response.read().decode('utf-8', errors='replace')
            except urllib.error.HTTPError as e:
                status_code = e.code
                content_type = (e.headers.get('Content-Type') or '').lower() if e.headers else ''
                body_text = e.read().decode('utf-8', errors='replace')
            except Exception as e:
                raise UserError(f'PAN verification request failed: {e}')

        if 'application/json' in (content_type or ''):
            try:
                data = json.loads(body_text or '{}')
            except Exception:
                data = {'raw': body_text}
        else:
            data = {'raw': body_text}

        if status_code >= 400:
            msg = data.get('message') if isinstance(data, dict) else False
            raise UserError(msg or f'PAN verification failed (HTTP {status_code}).')

        name = self._extract_name(data)
        valid = self._extract_valid(data)
        message = self._extract_message(data)
        active_status = self._extract_active_status(data)
        holder_type = self._extract_holder_type(data, pan)
        
        return {
            'pan': pan,
            'name': name,
            'valid': valid,
            'message': message,
            'active_status': active_status,
            'holder_type': holder_type,
            'raw': json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data,
        }
