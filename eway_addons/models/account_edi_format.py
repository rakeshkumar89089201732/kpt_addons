# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import json
from datetime import timedelta

from odoo import models, fields, api, _
from odoo.tools import html_escape
from odoo.exceptions import AccessError
from odoo.addons.iap import jsonrpc
from odoo.addons.l10n_in_edi.models.account_edi_format import DEFAULT_IAP_ENDPOINT, DEFAULT_IAP_TEST_ENDPOINT

from .error_codes import ERROR_CODES

import logging

_logger = logging.getLogger(__name__)


class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    # buyer and party details..........................
    def _get_l10n_in_edi_saler_buyer_party(self, move):
        res = super()._get_l10n_in_edi_saler_buyer_party(move)
        if move.is_purchase_document(include_receipts=True):
            res = {
                "seller_details": move.partner_id,
                "dispatch_details": move.partner_shipping_id or move.partner_id,
                "buyer_details": move.company_id.partner_id,
                "ship_to_details": move._l10n_in_get_warehouse_address() or move.company_id.ship_to,
            }
        return res

    # round value details................................
    @api.model
    def _l10n_in_round_value(self, amount, precision_digits=2):
        """
            This method is call for rounding.
            If anything is wrong with rounding then we quick fix in method
        """
        value = round(amount, precision_digits)
        # avoid -0.0
        return value if value else 0.0

    # E-way Bill json creation ....................................
    def _l10n_in_edi_ewaybill_generate_json(self, invoices):
        # def get_transaction_type(seller_details, dispatch_details, buyer_details, ship_to_details):
        #     """
        #         1 - Regular
        #         2 - Bill To - Ship To
        #         3 - Bill From - Dispatch From
        #         4 - Combination of 2 and 3
        #     """
        #     if seller_details != dispatch_details and buyer_details != ship_to_details:
        #         return 4
        #     elif seller_details != dispatch_details:
        #         return 3
        #     elif buyer_details != ship_to_details:
        #         return 2
        #     else:
        #         return 1
        saler_buyer = self._get_l10n_in_edi_saler_buyer_party(invoices)
        seller_details = saler_buyer.get("seller_details")
        dispatch_details = saler_buyer.get("dispatch_details")
        buyer_details = saler_buyer.get("buyer_details")
        ship_to_details = saler_buyer.get("ship_to_details")
        sign = invoices.is_inbound() and -1 or 1
        extract_digits = self._l10n_in_edi_extract_digits
        tax_details = self._l10n_in_prepare_edi_tax_details(invoices)
        tax_details_by_code = self._get_l10n_in_tax_details_by_line_code(tax_details.get("tax_details", {}))
        invoice_line_tax_details = tax_details.get("tax_details_per_record")
        line_items = []
        for line in invoices.invoice_line_ids:
            line_tax_details = invoice_line_tax_details.get(line.id, {})
            line_details = self._get_l10n_in_edi_ewaybill_line_details(line, line_tax_details, sign)
            line_items.append(line_details)
        json_payload = {
            "supplyType": invoices.supply_type,
            "subSupplyType": invoices.sub_type,
            "docType": invoices.document_type,
            "docNo": invoices.is_purchase_document(include_receipts=True) and invoices.ref or invoices.name,
            "docDate": invoices.document_date.strftime("%d/%m/%Y"),
            "transactionType": int(invoices.transaction_type),
            "fromGstin": seller_details.commercial_partner_id.vat or "URP",
            "fromTrdName": seller_details.commercial_partner_id.name,
            "fromAddr1": dispatch_details.street or "",
            "fromAddr2": dispatch_details.street2 or "",
            "fromPlace": dispatch_details.city or "",
            "fromPincode": dispatch_details.country_id.code == "IN" and int(extract_digits(dispatch_details.zip)) or "",
            "fromStateCode": int(seller_details.state_id.l10n_in_tin) or "",
            "actFromStateCode": dispatch_details.state_id.l10n_in_tin and int(
                dispatch_details.state_id.l10n_in_tin) or "",
            "toGstin": buyer_details.commercial_partner_id.vat or "URP",
            "toTrdName": buyer_details.commercial_partner_id.name,
            "toAddr1": invoices.partner_shipping_id.street or "",
            "toAddr2": invoices.partner_shipping_id.street2 or "",
            "toPlace": invoices.partner_shipping_id.city or "",
            "toPincode": int(extract_digits(invoices.partner_shipping_id.zip)),
            "actToStateCode": int(invoices.partner_shipping_id.state_id.l10n_in_tin),
            "toStateCode": invoices.l10n_in_state_id.l10n_in_tin and int(invoices.l10n_in_state_id.l10n_in_tin) or (
                    buyer_details.state_id.l10n_in_tin or int(buyer_details.state_id.l10n_in_tin) or ""),
            "transDistance": str(invoices.l10n_in_distance),
            'transporterId': invoices.transport_id,
            'transMode': invoices.transport_mode,
            'vehicleType': invoices.vehicle_type,
            'vehicleNo': invoices.transport_vehicle_no,
            'transDocNo': invoices.transportation_doc,
            'transDocDate': invoices.transportation_doc_date.strftime("%d/%m/%Y"),
            "itemList": line_items,
            "totalValue": self._l10n_in_round_value(tax_details.get("base_amount")),
            "cgstValue": self._l10n_in_round_value(tax_details_by_code.get("cgst_amount", 0.00)),
            "sgstValue": self._l10n_in_round_value(tax_details_by_code.get("sgst_amount", 0.00)),
            "igstValue": self._l10n_in_round_value(tax_details_by_code.get("igst_amount", 0.00)),
            "cessValue": self._l10n_in_round_value(tax_details_by_code.get("cess_amount", 0.00)),
            "cessNonAdvolValue": self._l10n_in_round_value(tax_details_by_code.get("cess_non_advol_amount", 0.00)),
            "otherValue": self._l10n_in_round_value(tax_details_by_code.get("other_amount", 0.00)),
            "totInvValue": self._l10n_in_round_value((tax_details.get("base_amount") + tax_details.get("tax_amount"))),
        }
        is_overseas = invoices.l10n_in_gst_treatment in ("overseas", "special_economic_zone")
        if invoices.is_purchase_document(include_receipts=True):
            if is_overseas:
                json_payload.update({"fromStateCode": 99})
            if is_overseas and dispatch_details.state_id.country_id.code != "IN":
                json_payload.update({
                    "actFromStateCode": 99,
                    "fromPincode": 999999,
                })
            else:
                json_payload.update({
                    "actFromStateCode": dispatch_details.state_id.l10n_in_tin and int(
                        dispatch_details.state_id.l10n_in_tin) or "",
                    "fromPincode": int(extract_digits(dispatch_details.zip)),
                })
        else:
            if is_overseas:
                json_payload.update({"toStateCode": 99})
            if is_overseas and ship_to_details.state_id.country_id.code != "IN":
                json_payload.update({
                    "actToStateCode": 99,
                    "toPincode": 999999,
                })
            else:
                json_payload.update({
                    "actToStateCode": int(ship_to_details.state_id.l10n_in_tin),
                    "toPincode": int(extract_digits(ship_to_details.zip)),
                })
            if invoices.enable_parta_slip:
                json_payload.update({
                    "transporterId": invoices.transport_id,
                    "transporterName": invoices.transporter_name or "",
                    "vehicleType": invoices.vehicle_type or "",
                })

            if invoices.enable_with_transport_based_eway_bill:
                json_payload.update({
                    "transMode": invoices.transport_mode2,
                    "vehicleType": invoices.vehicle_type or "",
                    "vehicleNo": invoices.transport_vehicle_no or "",
                    "transporterId": invoices.transport_id or "",
                    "transporterName": invoices.transporter_name or "",
                    "transDocNo": invoices.transportation_doc or "",
                    "transDocDate": invoices.transportation_doc_date.strftime(
                        "%d/%m/%Y") if invoices.transportation_doc_date else "",
                })

            if invoices.enable_without_transport_based_eway_bill:
                json_payload.update({
                    "transMode": invoices.transport_mode3,
                    "vehicleType": invoices.vehicle_type or "",
                    "vehicleNo": invoices.transport_vehicle_no or "",
                    "transDocNo": invoices.transportation_doc or "",
                    "transDocDate": invoices.transportation_doc_date.strftime(
                        "%d/%m/%Y") if invoices.transportation_doc_date else "",
                })

            if invoices.enable_without_transport_based_eway_bill:
                if invoices.transport_mode3 in ("3", "4"):
                    json_payload.update({
                        "transDocNo": invoices.transportation_doc or "",
                        "transDocDate": invoices.transportation_doc_date.strftime(
                            "%d/%m/%Y") if invoices.transportation_doc_date else "",
                    })

            if invoices.enable_with_transport_based_eway_bill:
                if invoices.sub_type == "8":
                    json_payload.update({
                        "subSupplyDesc": invoices.others_remarks,
                    })

            if invoices.enable_without_transport_based_eway_bill:
                if invoices.sub_type == "8":
                    json_payload.update({
                        "subSupplyDesc": invoices.others_remarks,
                    })
        return json_payload

    def _get_l10n_in_edi_ewaybill_line_details(self, line, line_tax_details, sign):
        extract_digits = self._l10n_in_edi_extract_digits
        tax_details_by_code = self._get_l10n_in_tax_details_by_line_code(line_tax_details.get("tax_details", {}))
        line_details = {
            "productName": line.product_id.name,
            "hsnCode": extract_digits(line.product_id.l10n_in_hsn_code),
            "productDesc": line.name[:100],
            "quantity": line.quantity,
            "qtyUnit": line.product_id.uom_id.l10n_in_code and line.product_id.uom_id.l10n_in_code.split("-")[
                0] or "OTH",
            "taxableAmount": self._l10n_in_round_value(line.balance * sign),
        }
        if tax_details_by_code.get("igst_rate") or (
                line.move_id.l10n_in_state_id.l10n_in_tin != line.company_id.state_id.l10n_in_tin):
            line_details.update({"igstRate": self._l10n_in_round_value(tax_details_by_code.get("igst_rate", 0.00))})
        else:
            line_details.update({
                "cgstRate": self._l10n_in_round_value(tax_details_by_code.get("cgst_rate", 0.00)),
                "sgstRate": self._l10n_in_round_value(tax_details_by_code.get("sgst_rate", 0.00)),
            })
        if tax_details_by_code.get("cess_rate"):
            line_details.update({"cessRate": self._l10n_in_round_value(tax_details_by_code.get("cess_rate"))})
        return line_details

    def _check_move_configuration(self, move):
        if self.code != "in_ewaybill_1_03":
            return super()._check_move_configuration(move)
        error_message = []
        base = self._l10n_in_edi_ewaybill_base_irn_or_direct(move)
        if not move.supply_type:
            error_message.append(_("Supply Type is Required"))
        if not move.sub_type:
            error_message.append(_("Sub Type is Required"))
        elif not move.transaction_type:
            error_message.append(_("Transaction Type is Required"))
        elif not move.transport_id:
            error_message.append(_("Transporter id is Required"))
        elif not move.transport_mode:
            error_message.append(_("Transporter Mode is Required"))
        elif not move.vehicle_type:
            error_message.append(_("Vechile Type is Required"))
        elif not move.transport_vehicle_no:
            error_message.append(_("Vehicle No is Required"))
        elif not move.transportation_doc:
            error_message.append(_("Transportation Doc No is Required"))
        elif not move.transportation_doc_date:
            error_message.append(_("Transportation Doc Date is Required"))
        if base == "irn":
            # already checked by E-invoice (l10n_in_edi) so no need to check
            return error_message
        is_purchase = move.is_purchase_document(include_receipts=True)
        error_message += self._l10n_in_validate_partner(move.partner_id)
        error_message += self._l10n_in_validate_partner(move.company_id.partner_id, is_company=True)
        if not re.match("^.{1,16}$", is_purchase and move.ref or move.name):
            error_message.append(_("%s number should be set and not more than 16 characters",
                (is_purchase and "Bill Reference" or "Invoice")))
        goods_line_is_available = False
        for line in move.invoice_line_ids.filtered(lambda line: not (line.display_type in ('line_section', 'line_note', 'rounding') or line.product_id.type == "service")):
            goods_line_is_available = True
            if line.product_id:
                hsn_code = self._l10n_in_edi_extract_digits(line.product_id.l10n_in_hsn_code)
                if not hsn_code:
                    error_message.append(_("HSN code is not set in product %s", line.product_id.name))
                elif not re.match("^[0-9]+$", hsn_code):
                    error_message.append(_(
                        "Invalid HSN Code (%s) in product %s", hsn_code, line.product_id.name
                    ))
            else:
                error_message.append(_("product is required to get HSN code"))
        if not goods_line_is_available:
            error_message.append(_('You need at least one product having "Product Type" as stockable or consumable.'))
        if error_message:
            error_message.insert(0, _("Impossible to send the Ewaybill."))
        return error_message




