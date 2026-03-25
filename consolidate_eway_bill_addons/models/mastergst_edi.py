from odoo import models, api, fields, _
import json
import requests
from odoo.exceptions import UserError
import logging
from .error_codes import MGT_ERROR_CODES
import base64

_logger = logging.getLogger(__name__)


class MastergstEdi(models.Model):
    _inherit = 'mastergst.edi'

    # get eway bill details
    def _get_eway_bill_details(self, ewaybill):
        self.mastergst_edi_authenticate(ewaybill.company_id)
        auth_url = (
            "https://api.whitebooks.in/ewaybillapi/v1.03/ewayapi/getewaybill"
            f"?email={ewaybill.company_id.email}&ewbNo={ewaybill.user_ewbNo}"
        )
        headers = {
            'ip_address': ewaybill.company_id.ip_address,
            'client_id': ewaybill.company_id.mastergst_client_id,
            'client_secret': ewaybill.company_id.mastergst_client_secret,
            'gstin': ewaybill.company_id.vat
        }
        params = {
            'email': ewaybill.company_id.email,
            'ewbNo': int(ewaybill.user_ewbNo)
        }

        try:
            response = requests.get(auth_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            response_json = response.json()

            if response_json.get("status_cd") == "1":
                data = json.dumps(response_json, indent=4)
                attachment = self.env['ir.attachment'].create({
                    'name': f"E_Way Bill {ewaybill.name}",
                    'type': 'binary',
                    'datas': base64.b64encode(data.encode('utf-8')),
                    'res_model': ewaybill._name,
                    'res_id': ewaybill.id,
                    'mimetype': 'application/json',
                })
                ewaybill.get_ewbNo_json = attachment
                return response_json
            else:
                error_msg_str = response_json.get("error", {}).get("message", "")
                error_code = None

                try:
                    error_json = json.loads(error_msg_str)
                    error_code = str(error_json.get("errorCodes"))
                except Exception:
                    pass

                if error_code:
                   user_message = MGT_ERROR_CODES.get(error_code, "Unknown error occurred.")
                   raise UserError(_("Error [%s]: %s") % (error_code, user_message))
                else:
                   raise UserError(_("Unknown API Error:%s") % error_msg_str)

        except requests.exceptions.RequestException as e:
            raise UserError(_("HTTP Request Error: %s") % str(e))
        except ValueError as ve:
            raise UserError(_("Response Parsing Error: %s") % str(ve))
