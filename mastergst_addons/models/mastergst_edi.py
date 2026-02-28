from odoo import models, api, fields, _
import json
import requests
from odoo.exceptions import UserError
import logging
from .error_codes import MGT_ERROR_CODES
import base64

_logger = logging.getLogger(__name__)

class MastergstEdi(models.Model):
    _name = 'mastergst.edi'

    # Part-B............................................................................................................
    # Part-B records is exist Validation error
    def check_already_exist_partb(self, move):
        domain = [
            ('invoice_no', '=', move.id),
            ('eway_no', '=', move.part_b_eway_bill_no if  move.part_b_eway_bill_no else move.eway_no),
            ('vehileno', '=', move.vehicle_no),
            ('fromplace', '=', move.from_place),
            ('fromstate', '=', move.fromState.id)
        ]
        existing = self.env['partb'].search(domain, limit=1)
        if existing:
            raise UserError(_("This Part-B record with the same vehicle details already exists. Please check before adding again."))

    # Part-B request send to E-Way bill Portal
    def _generate_partb(self, move):
        self._check_auth_validation(move.company_id)
        self._check_partb_validation(move)
        self.check_already_exist_partb(move)
        self.mastergst_edi_authenticate(move.company_id)
        auth_url = (
            "https://api.whitebooks.in/ewaybillapi/v1.03/ewayapi/vehewb"
            f"?email={move.company_id.email}"
        )
        headers = {
            'ip_address': move.company_id.ip_address,
            'client_id': move.company_id.mastergst_client_id,
            'client_secret': move.company_id.mastergst_client_secret,
            'gstin': move.company_id.vat,
        }
        json_payload = {
            "ewbNo": int(move.eway_no),
            "vehicleNo": move.vehicle_no,
            "fromPlace": move.from_place,
            "fromState": int(move.fromState.l10n_in_tin),
            "reasonCode": move.reason_codes,
            "reasonRem": move.reason_remarks,
            "transDocNo": move.trans_doc_no,
            "transDocDate": move.trans_doc_date.strftime("%d/%m/%Y"),
            "transMode": move.transportation_mode,
        }
        try:
            response = requests.post(auth_url, headers=headers, json=json_payload, timeout=20)
            response.raise_for_status()
            response_json = response.json()

            if response_json.get("status_cd") == "1":
                self._create_attachment(move, f'{move.name}Part-B', json.dumps(response_json, indent=4))
                self.get_partb_ewaybill_details(move)
                # Rainbow man success notification
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Part-B Vehicle is successfully Added'),
                        'type': 'success',
                        'sticky': False,
                        'next': {'type': 'ir.actions.act_window_close'},  # Optional
                    }
                }
                # return response_json
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

    # After create the Part-B get the Final Eway bill in Portal
    def get_partb_ewaybill_details(self, move):
       self.mastergst_edi_authenticate(move.company_id)
       auth_url = (
           "https://api.whitebooks.in/ewaybillapi/v1.03/ewayapi/getewaybill"
           f"?email={move.company_id.email}&ewbNo={move.eway_no}"
       )
       headers = {
           'ip_address': move.company_id.ip_address,
           'client_id': move.company_id.mastergst_client_id,
           'client_secret': move.company_id.mastergst_client_secret,
           'gstin': move.company_id.vat
       }
       params = {
           'email': move.company_id.email,
           'ewbNo': int(move.eway_no)
       }

       try:
           response = requests.get(auth_url, headers=headers, params=params, timeout=20)
           response.raise_for_status()
           response_json = response.json()

           if response_json.get("status_cd") == "1":
               self._create_attachment(move, f"{move.name}_Final_Part_B_JSON", json.dumps(response_json, indent=4))
               self.partb_create_record(move, response_json)
               # Rainbow man success notification
               return {
                   'type': 'ir.actions.client',
                   'tag': 'display_notification',
                   'params': {
                       'title': _('Success'),
                       'message': _('Part-B successfully Created.'),
                       'type': 'success',
                       'sticky': False,
                       'next': {'type': 'ir.actions.act_window_close'},  # Optional
                   }
               }
               # return response_json
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

    # Part-B record creation based on the Final Json
    def partb_create_record(self, move, response_json):
        eway_data = response_json.get('data', {})
        vehicle_list = eway_data.get('VehiclListDetails', [])

        for vehicle in vehicle_list:
            existing_from_state_code = vehicle.get("fromState")
            existing_veh_from_state = str(existing_from_state_code).zfill(2)
            ex_veh_from_state_id = self.env['res.country.state'].search([('l10n_in_tin', '=', existing_veh_from_state)], limit=1)
            existing_partb = self.env['partb'].search([
                ('invoice_no', '=', move.id),
                ('eway_no', '=', eway_data.get("ewbNo")),
                ('vehileno', '=', vehicle.get("vehicleNo")),
                ('fromplace', '=', vehicle.get("fromPlace")),
                ('fromstate', '=', ex_veh_from_state_id.id),
            ], limit=1)

            if existing_partb:
                # Skip if record already exists
                continue
            veh_from_state_code = vehicle.get("fromState")
            veh_from_state = str(veh_from_state_code).zfill(2)
            veh_from_state_id = self.env['res.country.state'].search([('l10n_in_tin', '=', veh_from_state)], limit=1)
            record = {
                'invoice_no': move.id,
                'eway_no': eway_data.get("ewbNo"),
                'ewaybilldate': eway_data.get("ewayBillDate"),
                'veupddate': vehicle.get("enteredDate"),
                'vehileno': vehicle.get("vehicleNo"),
                'fromplace': vehicle.get("fromPlace"),
                'fromstate': veh_from_state_id.id,
                'reasoncode': move.reason_codes,
                'reasonrem': move.reason_remarks,
                'transdocno': vehicle.get("transDocNo"),
                'transdocdate': vehicle.get("transDocDate"),
                'transmode': vehicle.get("transMode"),
                'state': 'post'
            }
            self.env['partb'].create(record)

    # Part-B Fields Validation
    def _check_partb_validation(self, move):
            if not move.eway_no:
                raise UserError("Please add the E-way No......!")
            elif not move.vehicle_no:
                raise UserError("Please Fill the vehicle_no.......!")
            elif not move.from_place:
                raise UserError("Please Fill the from_place........!")
            elif not move.fromState:
                raise UserError("Please Fill the fromState.......!")
            elif not move.reason_codes:
                raise UserError("Please Fill the reason_codes.......!")
            elif not move.reason_remarks:
                raise UserError("Please Fill the reason_remarks........!")
            elif not move.trans_doc_no:
                raise UserError("Please Fill the trans_doc_no..........!")
            elif not move.trans_doc_date:
                raise UserError("Please Fill the trans_doc_date.........!")
            elif not move.transportation_mode:
                raise UserError("Please Fill the transportation_mode.......!")

    # Initiate Multivehicle.............................................................................................

    def _initiate_multivehicle(self, move):
        self.mastergst_edi_authenticate(move.company_id)
        self._check_initiate_vehicle_validation(move)
        auth_url = ("https://api.whitebooks.in/ewaybillapi/v1.03/ewayapi/initmulti"
                    f"?email={move.company_id.email}")

        if not move.initiate_multi_vehicle:
            raise UserError("Do you want to initiate multi-vehicle? Please enable 'Initiate Multi Vehicle'.")

        headers = {
            'client_id': move.company_id.mastergst_client_id,
            'client_secret': move.company_id.mastergst_client_secret,
            'gstin': move.company_id.vat,
            'ip_address': move.company_id.ip_address,
            'Content-Type': 'application/json'
        }

        json_payload = {
            "ewbNo": int(move.initiate_ewb_no),
            "fromPlace": move.initiate_from_place,
            "fromState": int(move.initiate_from_state.l10n_in_tin),
            "toPlace": move.initiate_to_place,
            "toState": int(move.initiate_to_state.l10n_in_tin),
            "reasonCode": move.initiate_reason,
            "reasonRem": move.initiate_reason_remarks,
            "totalQuantity": move.initiate_total_quantity,
            "unitCode": move.initiate_unit_code,
            "transMode": move.initiate_mode_of_transport
        }

        try:
            response = requests.post(auth_url, headers=headers, json=json_payload, timeout=10)
            response.raise_for_status()
            response_json = response.json()

            print("Response Json:", response_json)

            if response_json.get("status_cd") == "1":
                self._create_attachment(move, f'{move.name}_Initiate_Vehicle_Res', json.dumps(response_json, indent=4))
                self._create_record_initiate_multivehicle(move, response_json)
                # Rainbow man success notification
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Multi-vehicle successfully initiated.'),
                        'type': 'success',
                        'sticky': False,
                        'next': {'type': 'ir.actions.act_window_close'},  # Optional
                    }
                }
                # return response_json
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

    # Create Initiate multi record
    def _create_record_initiate_multivehicle(self, move, response_json):
        record = {
            'name': move.name,
            'invoice_no': move.id,
            'create_date': fields.Datetime.now,
            'veh_ewb_no': response_json.get('data', {}).get("ewbNo"),
            'veh_from_place': move.initiate_from_place,
            'veh_from_state': move.initiate_from_state.id,
            'veh_to_place': move.initiate_to_place,
            'veh_to_state': move.initiate_to_state.id,
            'veh_reason': move.initiate_reason,
            'veh_reason_remarks': move.initiate_reason_remarks,
            'veh_total_quantity': move.initiate_total_quantity,
            'veh_unit_code': move.initiate_unit_code,
            'veh_mode_of_transport': move.initiate_mode_of_transport,
            'initiate_group_no': response_json.get('data', {}).get("groupNo"),
            'initiate_created_date': response_json.get('data', {}).get("createdDate"),
            'state': 'post'
        }
        self.env['initiate.multivehicle'].create(record)

    # Check Initiate Vehicle Validation
    def _check_initiate_vehicle_validation(self, move):
            if not move.initiate_ewb_no:
                raise UserError(_("Please Add the E-Way bill no"))
            elif not move.initiate_from_place:
                raise UserError(_("Please add the From Place"))
            elif not move.initiate_from_state:
                raise UserError(_("Please add the From State"))
            elif not move.initiate_to_place:
                raise UserError(_("Please add the To Place"))
            elif not move.initiate_to_state:
                raise UserError(_("Please add the To State"))
            elif not move.initiate_reason:
                raise UserError(_("Please add the Reason"))
            elif not move.initiate_reason_remarks:
                raise UserError(_("please add the Reason Remarks"))
            elif not move.initiate_total_quantity:
                raise UserError(_("Please add the Total Quantity"))
            elif not move.initiate_unit_code:
                raise UserError(_("Please add the Unit"))
            elif not move.initiate_mode_of_transport:
                raise UserError(_("Please add the transMode"))

    # Add the Multivehicle..............................................................................................

    def _generate_add_multivehicle(self, move):
        self._check_add_multivehicle_validation(move)
        auth_url= ("https://api.whitebooks.in/ewaybillapi/v1.03/ewayapi/addmulti"
            f"?email={move.company_id.email}")

        headers={
            'ip_address ': move.company_id.ip_address,
            'client_id': move.company_id.mastergst_client_id,
            'client_secret ': move.company_id.mastergst_client_secret,
            'gstin': move.company_id.vat,
            'Content-Type': 'application/json'
        }

        json_payload = {
            "ewbNo": int(move.add_multi_eway_no),
            "vehicleNo": move.add_multi_vehicle_no,
            "groupNo": str(move.add_multi_group_no),
            "transDocNo": move.add_multi_trans_doc_no,
            "transDocDate": move.add_multi_trans_doc_date.strftime("%d/%m/%Y"),
            "quantity": float(move.add_multi_quantity)
        }
        print("JSON:", json_payload)

        try:
            response = requests.post(auth_url, headers=headers, json=json_payload, timeout=10)
            response.raise_for_status()
            response_json = response.json()

            print("Response Json:", response_json)

            if response_json.get("status_cd") == "1":
                self._create_attachment(move, f'{move.name}_Add_Vehicle_Res', json.dumps(response_json, indent=4))
                self._create_add_multivehicle(move, response_json)
                # Rainbow man success notification
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Multi-vehicle successfully Added.'),
                        'type': 'success',
                        'sticky': False,
                        'next': {'type': 'ir.actions.act_window_close'},  # Optional
                    }
                }
                # return response_json
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

    # Add Multivehicle Record Creation
    def _create_add_multivehicle(self, move, response_json):
        eway_data = response_json.get('data', {})
        record = {
            "invoice_no": move.id,
            "ewbNo": move.add_multi_eway_no,
            "initiate_id": move.initiate_group_id.id,
            "from_place": move.initiate_group_id.veh_from_place,
            "vehicleNo": move.add_multi_vehicle_no,
            "groupNo": move.add_multi_group_no,
            "transDocNo":move.add_multi_trans_doc_no,
            "transDocDate": move.add_multi_trans_doc_date,
            "quantity": move.add_multi_quantity,
            "vehAddedDate": eway_data.get('vehAddedDate'),
            "vehicle_mode": move.initiate_group_id.veh_mode_of_transport,
            "state": 'post'
        }
        self.env['add.multivehicle'].create(record)

    # Check Add Multivehicle Validation
    def _check_add_multivehicle_validation(self, move):
        if not move.add_multi_eway_no:
            raise UserError(_("Please add the E-Way No"))
        elif not move.add_multi_vehicle_no:
            raise UserError(_("Please add the Vehicle No"))
        elif not move.add_multi_group_no:
            raise UserError(_("Please add the Initiate Group Name"))
        elif not move.add_multi_trans_doc_no:
            raise UserError(_("Please add the Vehicle Trans Doc No"))
        elif not move.add_multi_trans_doc_date:
            raise UserError(_("Please add the Vehicle Trans Doc Date"))

    # Change the multivehicle...........................................................................................

    def _change_multivehicle(self, move):
        self._check_change_multivehicle_validation(move)
        self.mastergst_edi_authenticate(move.company_id)
        auth_url = (
            "https://api.whitebooks.in/ewaybillapi/v1.03/ewayapi/updtmulti"
            f"?email={move.company_id.email}"
        )
        headers = {
            'ip_address ': move.company_id.ip_address,
            'client_id': move.company_id.mastergst_client_id,
            'client_secret ': move.company_id.mastergst_client_secret,
            'gstin': move.company_id.vat,
            'Content-Type': 'application/json'
        }

        json_payload = {
            "ewbNo": int(move.update_eway_no),
            "groupNo": int(move.update_group_no),
            "oldvehicleNo": move.update_old_veh_no.name,
            "newVehicleNo": move.update_new_vehicle_no,
            "oldTranNo": move.update_old_trans_doc_no,
            "newTranNo": move.update_new_trans_doc_no,
            "fromPlace": move.update_from_place,
            "fromState": int(move.update_from_state.l10n_in_tin),
            "reasonCode": move.update_reason_code,
            "reasonRem": move.update_reason_remarks
        }
        print("Update Json:", json_payload)
        try:
            response = requests.post(auth_url, headers=headers, json=json_payload, timeout=10)
            response.raise_for_status()
            response_json = response.json()

            print("Response Json:", response_json)

            if response_json.get('status_cd') == "1":
                self._create_attachment(move, f'{move.name}_Change_Vehicle', json.dumps(response_json, indent=4))
                self._create_change_vehicle_record(move, response_json)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Multi-vehicle Changed successfully.'),
                        'type': 'success',
                        'sticky': False,
                        'next': {'type': 'ir.actions.act_window_close'},  # Optional
                    }
                }
                # return response_json
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

    # Check Change Multivehicle Validation
    def _check_change_multivehicle_validation(self, move):
        if not move.update_eway_no:
            raise UserError(_("Please add the E-Way No"))
        elif not move.update_group_name:
            raise UserError(_("Please add the Initiate Group Name"))
        elif not move.update_old_veh_no:
            raise UserError(_("Please add the Old Vehicle No"))
        elif not move.update_new_vehicle_no:
            raise UserError(_("Please add the New Vehicle No"))
        elif not move.update_new_trans_doc_no:
            raise UserError(_("Please add the New Trans Doc No"))
        elif not move.update_from_place:
            raise UserError(_("Please add the From Place"))
        elif not move.update_from_state:
            raise UserError(_("Please add the From State"))
        elif not move.update_reason_code:
            raise UserError(_("Please add the Reason"))
        elif not move.update_reason_remarks:
            raise UserError(_("Please add the Reason Remarks"))

    # Add Record in Change Multivehicle Model
    def _create_change_vehicle_record(self,move,response_json):
        change_vehicle_json = response_json.get('data', {})
        change_record = {
            "change_invoice_no": move.id,
            "change_ewbNo": move.update_eway_no,
            "change_group_name": move.update_group_name.id,
            "change_groupNo": move.update_group_no,
            "change_vehUpdDate": change_vehicle_json.get('vehUpdDate'),
            "change_old_vehno": move.update_old_veh_no.name,
            "change_new_vehno": move.update_new_vehicle_no,
            "change_old_docno": move.update_old_trans_doc_no,
            "change_new_docno": move.update_new_trans_doc_no,
            "change_from_place": move.update_from_place,
            "change_from_state": move.update_from_state.id,
            "change_reason": move.update_reason_code,
            "change_remarks": move.update_reason_remarks,
            "state": 'post'
        }

        add_vehicle_record = {
            "invoice_no": move.id,
            "ewbNo": move.update_eway_no,
            "initiate_id": move.update_group_name.id,
            "vehicleNo": move.update_new_vehicle_no,
            "from_place": move.update_from_place,
            "groupNo": move.update_group_no,
            "transDocNo": move.update_new_trans_doc_no,
            "transDocDate": change_vehicle_json.get('vehUpdDate'),
            "quantity": move.update_group_name.veh_total_quantity,
            "vehAddedDate": change_vehicle_json.get('vehUpdDate'),
            "vehicle_mode": move.update_group_name.veh_mode_of_transport,
            "state": 'post'
        }
        get_veh = self.env['add.multivehicle'].search([('vehicleNo', '=', move.update_old_veh_no.name)])
        get_veh.write({'state': 'cancel'})
        self.env['change.multivehicle'].create(change_record)
        self.env['add.multivehicle'].create(add_vehicle_record)

    # Create a attachment...............................................................................................

    def _create_attachment(self, move, name, data):
        """
        Creates an attachment in Odoo for the given move, name, and data.
        """
        self.env['ir.attachment'].create({
            'name': name,
            'type': 'binary',
            'datas': base64.b64encode(data.encode('utf-8')),
            'res_model': move._name,
            'res_id': move.id,
            'mimetype': 'application/json',
        })

    # MasterGST Edi Authentication .....................................................................................

    @api.model
    def mastergst_edi_authenticate(self, company):
        self._check_auth_validation(company)
        url_path = (
            "https://api.whitebooks.in/ewaybillapi/v1.03/authenticate"
            f"?email={company.sudo().email}&username={company.sudo().mastergst_username}&password={company.sudo().mastergst_password}"
        )

        headers = {
            "email": company.email,
            "username": company.sudo().mastergst_username,
            "password": company.sudo().mastergst_password,
            "ip_address": company.sudo().ip_address,
            "client_id": company.sudo().mastergst_client_id,
            "client_secret": company.sudo().mastergst_client_secret,
            "gstin": company.vat
        }

        try:
            response = requests.get(url_path, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status_cd") == "1":
                    return {
                        "data": data,
                        "notification": {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _("Success"),
                                'type': 'success',
                                'message': _("Authentication Successful"),
                                'sticky': False,
                            },
                        }
                    }
                else:
                    status_desc = data.get("status_desc", "Authentication failed.")
            else:
                status_desc = f"HTTP Error: {response.status_code}"
        except requests.exceptions.RequestException as e:
            status_desc = f"Request failed: {str(e)}"

        return {
            "notification": {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Authentication Failed"),
                    'type': 'danger',
                    'message': _("Error: %s") % status_desc,
                    'sticky': False,
                },
            }
        }

    # Check Mastergst authentication fields(mastergst_username, mastergst_password, mastergst_client_id,
    # mastergst_client_secret, ip_address, vat, email)

    def _check_auth_validation(self, company):
        company = company.sudo()
        if not company.mastergst_username:
            raise UserError("Please add the MasterGST Username.")
        elif not company.mastergst_password:
            raise UserError("Please add the MasterGST Password.")
        elif not company.mastergst_client_id:
            raise UserError("Please add the MasterGST Client ID.")
        elif not company.mastergst_client_secret:
            raise UserError("Please add the MasterGST Client Secret.")
        elif not company.ip_address:
            raise UserError("Please add the IP Address.")
        elif not company.vat:
            raise UserError("Please add the Company GST Number.")
        elif not company.email:
            raise UserError("Please add the Company Email ID.")

























