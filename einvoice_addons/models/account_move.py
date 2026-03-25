# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import code128
import qrcode
import base64
import json
import re
from io import BytesIO
import io


class AccountMove(models.Model):
    _inherit = "account.move"

    # E_invoice Fields
    ack_no = fields.Char(string='ack_no', store=True)
    ack_date = fields.Char(string='ack_date', store=True)
    irn = fields.Char(string='IRN', store=True)
    signed_qr = fields.Char(string='signed QR', store=True)
    e_qr_code = fields.Binary(string='E-Invoice QR Code', store=True, compute='generate_signed_qr_code')
    e_barcode = fields.Binary(string='E-Invoice Barcode', store=True, compute='einvoice_generate_barcode',
                              inverse='einvoice_inverse_barcode')
    cancel_irn = fields.Char(string="E-invoice Cancelled Irn", store=True)
    cancel_date = fields.Char(string="E-Invoice Cancelled Date", store=True)
    ship_to = fields.Many2one(comodel_name='res.partner', string='Ship To', store=True)
    current_date = fields.Datetime(string='Print Date', store=True)

    # E-invoice JSON File Details
    def print_cancel_einvoice_data(self):
        for record in self:
            einvoice_cancel_data = None
            dynamic_part = record.name.replace('/', '_')
            einvoice_file_pattern = f"{dynamic_part}_cancel_einvoice.json"

            if record.attachment_ids:
                for attachment in record.attachment_ids:
                    if re.match(f".*{dynamic_part}_cancel_einvoice\.json$", attachment.name):
                        einvoice_cancel_data = base64.b64decode(attachment.datas).decode('utf-8')
                        break
            if einvoice_cancel_data:
                try:
                    einvoice_json = json.loads(einvoice_cancel_data)
                    record.cancel_irn = einvoice_json.get('Irn', '')  # Store as char directly
                    record.cancel_date = einvoice_json.get('CancelDate', '')  # Store as char directly
                    print(json.dumps(einvoice_json, indent=4))  # Pretty-print the JSON data
                except json.JSONDecodeError:
                    print('Error decoding JSON data from the file.')
                except ValueError as e:
                    print(f'Error parsing date: {e}')
            else:
                print(f'E-Invoice Bill JSON file matching pattern {einvoice_file_pattern} not found.')
            return True

    # E-invoice JSON File
    def print_einvoice_data(self):
        for record in self:
            einvoice_data = None
            dynamic_part = record.name.replace('/', '_')
            einvoice_file_pattern = f"{dynamic_part}_einvoice.json"

            if record.attachment_ids:
                for attachment in record.attachment_ids:
                    if re.match(f".*{dynamic_part}_einvoice\.json$", attachment.name):
                        einvoice_data = base64.b64decode(attachment.datas).decode('utf-8')
                        break
            if einvoice_data:
                try:
                    einvoice_json = json.loads(einvoice_data)
                    # Extract data and store in fields
                    record.ack_no = str(einvoice_json.get('AckNo', ''))
                    record.ack_date = einvoice_json.get('AckDt', '')  # Store as char directly
                    record.irn = einvoice_json.get('Irn', '')  # Store as char directly
                    record.signed_qr = einvoice_json.get('SignedQRCode', '')  # Store as char directly
                    print('E-Invoice Data:')
                    print(json.dumps(einvoice_json, indent=4))  # Pretty-print the JSON data
                except json.JSONDecodeError:
                    print('Error decoding JSON data from the file.')
                except ValueError as e:
                    print(f'Error parsing date: {e}')
            else:
                print(f'E-way Bill JSON file matching pattern {einvoice_file_pattern} not found.')
            return True

    # E-Invoice Generate QR Code
    @api.depends('signed_qr')
    def generate_signed_qr_code(self):
        for rec in self:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=3,
                border=4,
            )
            qr_data = f"{rec.signed_qr}"
            qr.add_data(qr_data)
            qr.make(fit=True)
            img = qr.make_image()
            temp = BytesIO()
            img.save(temp, format="PNG")
            qr_image = base64.b64encode(temp.getvalue())
            rec.e_qr_code = qr_image
            print(rec.e_qr_code)

    # E-Invoice Remove QR Code
    def invoice_remove_qr_code(self):
        for rec in self:
            rec.e_qr_code = False

    # E-invoice  Barcode
    @api.depends('ack_no')
    def einvoice_generate_barcode(self):
        for rec in self:
            if rec.ack_no:
                barcode_param = rec.ack_no
                barcode_bytes = io.BytesIO()
                barcode = code128.image(barcode_param, height=80).save(barcode_bytes, "PNG")
                barcode_bytes.seek(0)
                image_data = base64.b64encode(barcode_bytes.read()).decode('utf-8')
                rec.e_barcode = image_data

    def einvoice_inverse_barcode(self):
        pass

    # E-invoice Remove  BarCode
    def einvoice_remove_barcode(self):
        for rec in self:
            rec.e_barcode = False



