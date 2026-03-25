import base64
import io
import json
import re
from collections import defaultdict
from io import BytesIO

import code128
import qrcode
# from barcode.writer import ImageWriter

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Old fields.........................................................................................
    # Transaction Details
    l10n_in_type_id = fields.Many2one("l10n.in.ewaybill.type", "E-waybill Document Type", tracking=True)
    # transportation details
    l10n_in_distance = fields.Integer("Distance", tracking=True)
    l10n_in_mode = fields.Selection([
        ("0", "Managed by Transporter"),
        ("1", "By Road"),
        ("2", "Rail"),
        ("3", "Air"),
        ("4", "Ship")],
        string="Transportation Mode", copy=False, tracking=True)
    # Vehicle Number and Type required when transportation mode is By Road.
    l10n_in_vehicle_no = fields.Char("Vehicle Number", copy=False, tracking=True)
    l10n_in_vehicle_type = fields.Selection([
        ("R", "Regular"),
        ("O", "ODC")],
        string="Vehicle Type", copy=False, tracking=True)
    # Document number and date required in case of transportation mode is Rail, Air or Ship.
    l10n_in_transportation_doc_no = fields.Char(
        string="E-waybill Document Number",
        help="""Transport document number. If it is more than 15 chars, last 15 chars may be entered""",
        copy=False, tracking=True)
    l10n_in_transportation_doc_date = fields.Date(
        string="Document Date",
        help="Date on the transporter document",
        copy=False,
        tracking=True)
    # transporter id required when transportation done by other party.
    l10n_in_transporter_id = fields.Many2one("res.partner", "Transporter", copy=False, tracking=True)
    # show and hide fields base on this
    l10n_in_edi_ewaybill_direct_api = fields.Boolean(string="E-waybill(IN) direct API",
                                                     compute="_compute_l10n_in_edi_ewaybill_direct")
    l10n_in_edi_ewaybill_show_send_button = fields.Boolean(string="Show Send E-waybill Button",
                                                           compute="_compute_l10n_in_edi_ewaybill_show_send_button")
    edi_document_ids = fields.One2many(
        comodel_name='account.edi.document',
        inverse_name='move_id')

    # New Fields................................................................................................
    supply_type = fields.Selection([
        ('O', 'Outward'),
        ('I', 'Inward')
    ], string="Supply Type", store=True)

    sub_type = fields.Selection([
        ('1', 'Supply'),
        ('2', 'Import'),
        ('3', 'SKD/CKD/Lots'),
        ('4', 'Job work Returns'),
        ('5', 'Sales Return'),
        ('6', 'Exhibition or Fairs'),
        ('7', 'For Own Use'),
        ('8', 'Others')
    ], string="Sub Type", store=True)
    document_type = fields.Selection([
        ('INV', 'Tax Invoice'),
        ('BIL', 'Bill of Supply'),
        ('CHL', 'Delivery Challan'),
        ('BOE', 'Bill of Entry'),
    ], string="Document Type", store=True)
    document_no = fields.Char(string='Document No', store=True, related='name')
    document_date = fields.Date(string='Document Date', store=True)
    transaction_type = fields.Selection([
        ('1', 'Regular'),
        ('2', 'Bill To - Ship To'),
        ('3', 'Bill From - Dispatch From'),
        ('4', 'Combination of 2 and 3'),
    ], string='Transaction Type', compute="_compute_transaction_type", store=True)
    # Transporter Details_______________________________________________________________
    transport_id = fields.Char(string='Transporter_id', store=True, copy=False, tracking=True)
    transporter_name = fields.Char(string='Transporter Name', store=True, copy=False)
    # km_distance = fields.Integer(string="Approximate Distance (in KM)", store=True)
    transport_mode = fields.Selection([
        ("0", "Managed by Transporter")],
        string="Transportation Mode", copy=False, tracking=True, default='0')

    transport_mode2 = fields.Selection([
        ("1", "By Road"),
        ("2", "Rail"),
        ("3", "Air"),
        ("4", "Ship or Ship Cum Road/Rail")
    ],
        string="Transportation Mode", copy=False, tracking=True, default='1')
    transport_mode3 = fields.Selection([
        ("1", "By Road"),
        ("2", "Rail"),
        ("3", "Air"),
        ("4", "Ship or Ship Cum Road/Rail")],
        string="Transportation Mode", copy=False, tracking=True, default='1')

    vehicle_type = fields.Selection([("R", "Regular"),
                                     ("O", "ODC")], copy=False, tracking=True)
    transport_vehicle_no = fields.Char("Vehicle Number", copy=False, tracking=True)
    transportation_doc = fields.Char("Transporter Doc No", store=True, copy=False, tracking=True)
    transportation_doc_date = fields.Date(
        string=" Transportation Doc Date",
        help="Date on the transporter document",
        store=True,
        copy=False,
        tracking=True)
    l10n_in_eway_cancel_reason = fields.Selection(selection=[
        ("1", "Duplicate"),
        ("2", "Data Entry Mistake"),
        ("3", "Order Cancelled"),
        ("4", "Others"),
    ], string="Cancel reason (E-way Bill)", copy=False, store=True)
    l10n_in_eway_cancel_remarks = fields.Char("Cancel remarks (E-way Bill)", copy=False, store=True)
    # New E-Way bill Details Fields_______________________________________________________________
    eway_no = fields.Char(string="E-Way Bill No", store=True)
    genrated_by = fields.Char(string='Genrated By', store=True, related='company_id.vat')
    eway_date = fields.Char(string="Generated Date", store=True)
    valid_upto = fields.Char(string="Valid Upto", store=True)
    qr_code = fields.Binary(store=True, compute="generate_qr_code")
    barcode = fields.Binary(string="Barcode", store=True, compute='_generate_barcode', inverse='_inverse_barcode')
    cancel_ewayno = fields.Char(string="Cancelled E-way Bill No", store=True)
    eway_cancel_date = fields.Char(string=" Cancelled E-way Bill Date", store=True)
    enable_parta_slip = fields.Boolean(string='Part-A', default=False, tracking=True)
    enable_with_transport_based_eway_bill = fields.Boolean(string='With Transporter', default=False, tracking=True)
    enable_without_transport_based_eway_bill = fields.Boolean(string='Without Transporter', default=False,
                                                              tracking=True)
    others_remarks = fields.Char(string='Description', store=True)
    # tax amount fields.................................................................................
    sgst_amount = fields.Float(string="SGST", compute='action_compute_tax_amount', digits=(16, 2))
    cgst_amount = fields.Float(string="CGST", compute='action_compute_tax_amount', digits=(16, 2))
    igst_amount = fields.Float(string="IGST", compute='action_compute_tax_amount', digits=(16, 2))
    cess_amt = fields.Float(string="CESS", compute='action_compute_tax_amount', digits=(16, 2))
    cess_non = fields.Float(string="CESS_NON_ADVOL", compute='action_compute_tax_amount', digits=(16, 2))
    other_amt = fields.Float(string='Others', compute='action_compute_tax_amount', digits=(16, 2))
    amount_total_vals = fields.Float(string='amount_total_vals', store=True, compute='compute_total_vals', digits=(16, 2))
    amount_untaxed_vals = fields.Float(string='amount_untaxed_vals', store=True, compute='compute_total_vals', digits=(16, 2))

    @api.onchange('enable_parta_slip')
    def _onchange_enable_parta_slip(self):
        if self.enable_parta_slip:
            self.enable_with_transport_based_eway_bill = False
            self.enable_without_transport_based_eway_bill = False

    @api.onchange('enable_with_transport_based_eway_bill')
    def _onchange_enable_with_transport_based_eway_bill(self):
        if self.enable_with_transport_based_eway_bill:
            self.enable_parta_slip = False
            self.enable_without_transport_based_eway_bill = False

    @api.onchange('enable_without_transport_based_eway_bill')
    def _onchange_enable_without_transport_based_eway_bill(self):
        if self.enable_without_transport_based_eway_bill:
            self.enable_parta_slip =  False
            self.enable_with_transport_based_eway_bill = False

    @api.depends('invoice_line_ids.tax_ids', 'invoice_line_ids.price_unit', 'amount_total', 'amount_untaxed', 'currency_id')
    def action_compute_tax_amount(self):
        for move in self:
            tax_details = {
                'SGST': 0.0,
                'CGST': 0.0,
                'IGST': 0.0,
                'CESS': 0.0,
                'CESS_NON_ADVOL': 0.0,
                'Others': 0.0
            }
            for line in move.invoice_line_ids:
                tax_lines = line.tax_ids.compute_all(line.price_unit * line.quantity, currency=line.currency_id, partner=line.partner_id)['taxes']

                for tax_line in tax_lines:
                    tax_id = tax_line.get('id')
                    tax_amount = tax_line.get('amount', 0.0)
                    tax = self.env['account.tax'].browse(tax_id)
                    if tax and tax.name:
                        if 'SGST' in tax.name:
                            tax_details['SGST'] += tax_amount
                        elif 'CGST' in tax.name:
                            tax_details['CGST'] += tax_amount
                        elif 'IGST' in tax.name:
                            tax_details['IGST'] += tax_amount
                        elif 'CESS' in tax.name:
                            if tax.amount_type != "percent":
                                tax_details['CESS_NON_ADVOL'] += tax_amount
                            else:
                                tax_details['CESS'] += tax_amount
                        else:
                            tax_details['Others'] += tax_amount
            move.update({
                'sgst_amount': tax_details['SGST'],
                'cgst_amount': tax_details['CGST'],
                'igst_amount': tax_details['IGST'],
                'cess_amt': tax_details['CESS'],
                'cess_non': tax_details['CESS_NON_ADVOL'],
                'other_amt': tax_details['Others'],
            })

    @api.depends('amount_total', 'amount_untaxed')
    def compute_total_vals(self):
        for rec in self:
            rec.amount_total_vals = rec.amount_total
            rec.amount_untaxed_vals = rec.amount_untaxed

    def button_cancel_posted_moves(self):
        """Mark the edi.document related to this move to be canceled."""
        reason_and_remarks_not_set = self.env["account.move"]
        for move in self:
            send_l10n_in_edi_ewaybill = move.edi_document_ids.filtered(
                lambda doc: doc.edi_format_id.code == "in_ewaybill_1_03")
            # check submitted E-waybill does not have reason and remarks
            # because it's needed to cancel E-waybill
            if send_l10n_in_edi_ewaybill and (
                    not move.l10n_in_eway_cancel_reason or not move.l10n_in_eway_cancel_remarks):
                reason_and_remarks_not_set += move
        if reason_and_remarks_not_set:
            raise UserError(_(
                "To cancel E-waybill set cancel reason and remarks at E-waybill tab in: \n%s",
                ("\n".join(reason_and_remarks_not_set.mapped("name"))),
            ))
        return super().eway_button_cancel_posted_moves()

    # E-Way Bill Cancel Data File
    def print_ewaybill_cancel_data(self):
        for record in self:
            ewaybill_cancel_data = None
            dynamic_part = record.name.replace('/', '_')
            ewaybill_file_pattern = f"{dynamic_part}_ewaybill_cancel.json"

            if record.attachment_ids:
                for attachment in record.attachment_ids:
                    if re.match(f".*{dynamic_part}_ewaybill_cancel.json$", attachment.name):
                        ewaybill_cancel_data = base64.b64decode(attachment.datas).decode('utf-8')
                        break
            if ewaybill_cancel_data:
                try:
                    ewaybill_json = json.loads(ewaybill_cancel_data)
                    # Extract data and store in fields
                    record.cancel_ewayno = str(ewaybill_json.get('ewayBillNo', ''))
                    record.eway_cancel_date = ewaybill_json.get('cancelDate', '')  # Store as char directly
                    print('E-way Bill Data:')
                    print(json.dumps(ewaybill_json, indent=4))  # Pretty-print the JSON data
                except json.JSONDecodeError:
                    print('Error decoding JSON data from the file.')
                except ValueError as e:
                    print(f'Error parsing date: {e}')
            else:
                print(f'E-way Bill JSON file matching pattern {ewaybill_file_pattern} not found.')

            return True

    # E-Way Bill Data File
    def print_ewaybill_data(self):
        for record in self:
            ewaybill_data = None
            dynamic_part = record.name.replace('/', '_')
            ewaybill_file_pattern = f"{dynamic_part}_ewaybill.json"

            if record.attachment_ids:
                for attachment in record.attachment_ids:
                    if re.match(f".*{dynamic_part}_ewaybill.json$", attachment.name):
                        ewaybill_data = base64.b64decode(attachment.datas).decode('utf-8')
                        break
            if ewaybill_data:
                try:
                    ewaybill_json = json.loads(ewaybill_data)
                    # Extract data and store in fields
                    record.eway_no = str(ewaybill_json.get('ewayBillNo', ''))
                    record.eway_date = ewaybill_json.get('ewayBillDate', '')  # Store as char directly
                    record.valid_upto = ewaybill_json.get('validUpto', '')  # Store as char directly
                    print('E-way Bill Data:')
                    print(json.dumps(ewaybill_json, indent=4))  # Pretty-print the JSON data
                except json.JSONDecodeError:
                    print('Error decoding JSON data from the file.')
                except ValueError as e:
                    print(f'Error parsing date: {e}')
            else:
                print(f'E-way Bill JSON file matching pattern {ewaybill_file_pattern} not found.')

            return True

    # E-Way Bill Generate QR Code
    @api.depends('eway_no', 'genrated_by', 'eway_date')
    def generate_qr_code(self):
        for rec in self:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=3,
                border=4,
            )
            # Format the date correctly for the QR code
            eway_date_str = rec.eway_date

            if eway_date_str:
                # Construct the data string for the QR code including additional fields
                qr_data = f"{rec.eway_no}/{rec.genrated_by}/{eway_date_str}"
                qr.add_data(qr_data)
                qr.make(fit=True)
                img = qr.make_image()
                temp = BytesIO()
                img.save(temp, format="PNG")
                qr_image = base64.b64encode(temp.getvalue())
                rec.qr_code = qr_image
                print(rec.qr_code)

    # E-Way Bill QR Code
    def remove_qr_code(self):
        for rec in self:
            rec.qr_code = False

    # E-Way Bill Barcode
    @api.depends('eway_no')
    def _generate_barcode(self):
        for rec in self:
            if rec.eway_no:
                barcode_param = rec.eway_no
                barcode_bytes = io.BytesIO()
                barcode = code128.image(barcode_param, height=80).save(barcode_bytes, "PNG")
                barcode_bytes.seek(0)
                image_data = base64.b64encode(barcode_bytes.read()).decode('utf-8')
                rec.barcode = image_data

    def _inverse_barcode(self):
        pass

    # E-Way Bill Remove  BarCode
    def remove_barcode(self):
        for rec in self:
            rec.barcode = False

    # download Part-A PDF
    def download_with_transporter_pdf(self):
        self.print_ewaybill_data()
        self.generate_qr_code()
        self._generate_barcode()
        return self.env.ref('eway_addons.action_eway_bill').report_action(self)

    def download_cancelled_transporter_pdf(self):
        self.print_ewaybill_cancel_data()
        return self.env.ref('eway_addons.action_eway_bill_cancelled').report_action(self)

    def download_parta_slip(self):
        self.print_ewaybill_data()
        self.generate_qr_code()
        self._generate_barcode()
        return self.env.ref('eway_addons.action_parta_slip').report_action(self)

    def download_cancelled_parta_slip(self):
        self.print_ewaybill_cancel_data()
        return self.env.ref('eway_addons.action_parta_canclled_slip').report_action(self)


    @api.depends('partner_id', 'partner_shipping_id')
    def _compute_transaction_type(self):
        for move in self:
            customer = move.invoice_origin and self.env['sale.order'].sudo().search(
                [('name', '=', move.invoice_origin)],
                limit=1
            ).partner_id

            if not customer:
                move.transaction_type = False
                continue

            invoice_partner = move.partner_id
            shipping_partner = move.partner_shipping_id

            # Case 1: Both same as customer → Regular
            if invoice_partner == customer and shipping_partner == customer:
                move.transaction_type = '1'
            # Case 4: Both different from customer → Combination
            elif invoice_partner != customer and shipping_partner != customer:
                move.transaction_type = '4'
            # Case 2: Only shipping differs
            elif invoice_partner == customer and shipping_partner != customer:
                move.transaction_type = '2'
            # Case 3: Only billing differs
            elif invoice_partner != customer and shipping_partner == customer:
                move.transaction_type = '3'
            else:
                move.transaction_type = False


