from odoo import models, api, fields, _
import json
import base64
from odoo.exceptions import ValidationError
import qrcode
from barcode import EAN13
from barcode.writer import ImageWriter
import code128
from io import BytesIO
import io
from odoo.exceptions import UserError

class GetEwaybill(models.Model):
    _name = 'get.ewaybill'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="name", related='user_ewbNo')
    user_ewbNo = fields.Char(string="Eway Bill No")

    get_ewbNo = fields.Char(string="ewbNo")
    get_ewayBillDate = fields.Char(string="ewayBillDate")
    get_genMode = fields.Char(string="Generation Mode")
    get_userGstin = fields.Char(string="User GSTIN")
    get_noValidDays = fields.Integer(string="Number of Valid Days")
    get_validUpto = fields.Char(string="Valid Upto")
    # Transaction based fields
    get_supplyType = fields.Selection([
        ('O', 'Outward'),
        ('I', 'Inward')
    ], string="supplyType", store=True)
    get_subSupplyType = fields.Selection([
        ('1', 'Supply'),
        ('2', 'Import'),
        ('3', 'Export'),
        ('4', 'Job work'),
        ('5', 'For Own Use'),
        ('6', 'Job work Returns'),
        ('7', 'Sales Return'),
        ('8', 'Others'),
        ('9', 'SKD/CKD/Lots'),
        ('10', 'Line Sales'),
        ("11", 'Recipient Not Known'),
        ('12', 'Exhibition or Fairs'),
    ], string="subSupplyType", store=True)
    get_docType = fields.Selection([
        ('INV', 'Tax Invoice'),
        ('BIL', 'Bill of Supply'),
        ('CHL', 'Delivery Challan'),
        ('BOE', 'Bill of Entry'),
        ('OTH', 'Others'),
    ], string="docType", store=True)
    get_transactionType = fields.Selection([
        ('1', 'Regular'),
        ('2', 'Bill To - Ship To'),
        ('3', 'Bill From - Dispatch From'),
        ('4', 'Combination of 2 and 3'),
    ], string='transactionType', store=True)
    get_vehicleType = fields.Selection([("R", "Regular"),
                                        ("O", "ODC")], copy=False, tracking=True, string="vehicleType")
    # bill From details
    get_billfrom_Gstin = fields.Char(string="Bill From GSTIN")
    get_billfrom_TrdName = fields.Char(string="Bill From Trade Name")
    get_billfrom_state = fields.Many2one(string="Bill From State", comodel_name='res.country.state')
    # Dispatch From Details
    get_dispatch_fromAddr1 = fields.Char(string="Dispatch From Address1")
    get_dispatch_fromAddr2 = fields.Char(string="Dispatch From Address2")
    get_dispatch_fromPlace = fields.Char(string="Dispatch From City")
    get_dispatch_fromPincode = fields.Char(string="Dispatch From Pincode")
    get_dispatch_fromStateCode = fields.Many2one(string="Dispatch From State", comodel_name='res.country.state')
    get_dispatch_actFromStateCode = fields.Char(string="Dispatch From State Code")
    # Bill To Details
    get_billto_Gstin = fields.Char(string="Bill To GSTIN")
    get_billto_TrdName = fields.Char(string="Bill To Trade Name")
    get_billto_StateCode = fields.Many2one(string="Bill To State", comodel_name='res.country.state')
    # Ship to Details
    get_shipto_Addr1 = fields.Char(string="Ship To Address 1")
    get_shipto_Addr2 = fields.Char(string="Ship To Address 2")
    get_shipto_Place = fields.Char(string="Ship To Place")
    get_shipto_Pincode = fields.Char(string="Ship To Pincode")
    get_shipto_StateCode = fields.Many2one(string="Ship To State", comodel_name='res.country.state')
    get_actToStateCode = fields.Char(string="Actual Ship To State Code")
    # Document details
    get_transporterId = fields.Char(string="Transporter ID")
    get_transporterName = fields.Char(string="Transporter Name")
    get_docNo = fields.Char(string="Document Number")
    get_docDate = fields.Char(string="Document Date")
    get_actualDist = fields.Integer(string="Actual Distance")
    # Total Details
    get_cgstValue = fields.Float(string="CGST Value")
    get_sgstValue = fields.Float(string="SGST Value")
    get_igstValue = fields.Float(string="IGST Value")
    get_cessValue = fields.Float(string="CESS Value")
    get_otherValue = fields.Float(string="Other Value")
    get_cessNonAdvolValue = fields.Float(string="Cess Non-Advol Value")
    get_totalValue = fields.Float(string="Total Value")
    get_totInvValue = fields.Float(string="Total Invoice Value")
    # Other Details
    get_status = fields.Char(string="Status")
    get_extendedTimes = fields.Integer(string="Extended Times")
    get_rejectStatus = fields.Char(string="Reject Status")
    # Product and Vehicle Details
    products_id = fields.One2many(comodel_name='get.products.ewaybill', inverse_name='product_ids', string="Products")
    vehicles_id = fields.One2many(comodel_name='get.ewaybill.vehicles', inverse_name='vehicles_ids', string="Vehicles")
    # Attachment Field
    get_ewbNo_json = fields.Many2many(comodel_name='ir.attachment', string='Eway Json')
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', 'Created By', default=lambda self: self.env.user)
    created_date = fields.Datetime(string='Created On', readonly=True, index=True, default=fields.Datetime.now)
    # Barcode and Qr code field
    get_eway_barcode = fields.Binary(string='Barcode')
    get_eway_qr_code = fields.Binary(string='Qr Code')

    # Get the eway bill details
    def get_eway_bill_details(self):
        return self.env['mastergst.edi']._get_eway_bill_details(self)

    # Add the eway bill details
    def read_ewaybill_json(self):
        self.ensure_one()

        if self.get_ewbNo_json:
            raise UserError(_("An E-Way Bill JSON is already attached. To download a new JSON, please remove the existing E-Way Bill JSON first."))

        self.get_eway_bill_details()
        for rec in self:
            if not rec.get_ewbNo_json:
                raise ValidationError("No attachment Found")

            data = base64.b64decode(rec.get_ewbNo_json.datas)
            data_str = data.decode('utf-8')
            json_data = json.loads(data_str)
            eway_data = json_data.get('data', {})
            product_list = eway_data.get('itemList', [])
            vehicle_list = eway_data.get('VehiclListDetails', [])

            # ewb details
            rec.get_ewbNo = eway_data.get("ewbNo")
            rec.get_ewayBillDate = eway_data.get("ewayBillDate")
            rec.get_genMode = eway_data.get("genMode")
            rec.get_userGstin = eway_data.get("userGstin")
            rec.get_noValidDays = eway_data.get("noValidDays")
            rec.get_validUpto = eway_data.get("validUpto")

            # transaction details
            rec.get_supplyType = eway_data.get("supplyType")
            rec.get_subSupplyType = str(eway_data.get("subSupplyType")).strip()
            rec.get_docType = eway_data.get("docType")
            rec.get_transactionType = str(eway_data.get("transactionType"))
            rec.get_vehicleType = eway_data.get("vehicleType")

            # bill from details
            rec.get_billfrom_Gstin = eway_data.get("fromGstin")
            rec.get_billfrom_TrdName = eway_data.get("fromTrdName")
            bill_from_state = eway_data.get("fromStateCode")
            bill_from_formatted_code = str(bill_from_state).zfill(2)
            vals = self.env['res.country.state'].search([('l10n_in_tin', '=', bill_from_formatted_code)], limit=1)
            rec.get_billfrom_state = vals.id

            # Dispatch From Details
            rec.get_dispatch_fromAddr1 = eway_data.get("fromAddr1")
            rec.get_dispatch_fromAddr2 = eway_data.get("fromAddr2")
            rec.get_dispatch_fromPlace = eway_data.get("fromPlace")
            rec.get_dispatch_fromPincode = eway_data.get("fromPincode")
            rec.get_dispatch_actFromStateCode = eway_data.get("actFromStateCode")
            dispatch_from_formatted_code = str(rec.get_dispatch_actFromStateCode).zfill(2)
            state_name = self.env['res.country.state'].search([('l10n_in_tin', '=', dispatch_from_formatted_code)], limit=1)
            rec.get_dispatch_fromStateCode = state_name.id

            # Bill to details
            rec.get_billto_Gstin = eway_data.get("toGstin")
            rec.get_billto_TrdName = eway_data.get("toTrdName")
            bill_to_state = eway_data.get("actToStateCode")
            bill_to_formatted_code = str(bill_to_state).zfill(2)
            bill_to_state_name = self.env['res.country.state'].search([('l10n_in_tin', '=', bill_to_formatted_code)],limit=1)
            rec.get_billto_StateCode = bill_to_state_name.id

            # Ship to Details
            rec.get_shipto_Addr1 = eway_data.get("toAddr1")
            rec.get_shipto_Addr2 = eway_data.get("toAddr2")
            rec.get_shipto_Place = eway_data.get("toPlace")
            rec.get_shipto_Pincode = eway_data.get("toPincode")
            rec.get_actToStateCode = eway_data.get("actToStateCode")
            to_formatted_code = str(rec.get_actToStateCode).zfill(2)
            to_state_name = self.env['res.country.state'].search([('l10n_in_tin', '=', to_formatted_code)], limit=1)
            rec.get_shipto_StateCode = to_state_name.id

            # document details
            rec.get_transporterId = eway_data.get("transporterId")
            rec.get_transporterName = eway_data.get("transporterName")
            rec.get_docNo = eway_data.get("docNo")
            rec.get_docDate = eway_data.get("docDate")
            rec.get_actualDist = eway_data.get("actualDist")

            # total values
            rec.get_cgstValue = eway_data.get("cgstValue")
            rec.get_sgstValue = eway_data.get("sgstValue")
            rec.get_igstValue = eway_data.get("igstValue")
            rec.get_cessValue = eway_data.get("cessValue")
            rec.get_otherValue = eway_data.get("otherValue")
            rec.get_cessNonAdvolValue = eway_data.get("cessNonAdvolValue")
            rec.get_totalValue = eway_data.get("totalValue")
            rec.get_totInvValue = eway_data.get("totInvValue")

            # other details
            rec.get_status = eway_data.get("status")
            rec.get_extendedTimes = eway_data.get("extendedTimes")
            rec.get_rejectStatus = eway_data.get("rejectStatus")

            # Clear existing One2many lines (if required)
            rec.products_id = [(5, 0, 0)]
            rec.vehicles_id = [(5, 0, 0)]

            # Prepare and assign product list
            product_vals = []
            for product in product_list:
                product_vals.append((0, 0, {
                    'get_eway_hsnCode': product.get("hsnCode"),
                    'get_eway_product_itemno': product.get("itemNo"),
                    'get_eway_product_id': product.get("productId"),
                    'get_eway_productName': product.get("productName"),
                    'get_eway_productDesc': product.get("productDesc"),
                    'get_eway_quantity': product.get("quantity"),
                    'get_eway_qtyUnit': product.get("qtyUnit"),
                    'get_eway_cgstRate': product.get("cgstRate"),
                    'get_eway_sgstRate': product.get("sgstRate"),
                    'get_eway_igstRate': product.get("igstRate"),
                    'get_eway_cessRate': product.get("cessRate"),
                    'get_eway_cessNonAdvol': product.get("cessNonAdvol"),
                    'get_eway_taxableAmount': product.get("taxableAmount"),
                }))
            rec.products_id = product_vals

            # Prepare and assign vehicle list
            vehicle_vals = []
            for vehicle in vehicle_list:
                veh_from_state_code = vehicle.get("fromState")
                veh_from_formatted_code = str(veh_from_state_code).zfill(2)
                state_name = self.env['res.country.state'].search([('l10n_in_tin', '=', veh_from_formatted_code)], limit=1)
                vehicle_vals.append((0, 0, {
                    'get_veh_updMode': vehicle.get("updMode"),
                    'get_veh_vehicleNo': vehicle.get("vehicleNo"),
                    'get_veh_fromPlace': vehicle.get("fromPlace"),
                    'get_veh_fromState': state_name.id,
                    'get_veh_tripshtNo': vehicle.get("tripshtNo"),
                    'get_veh_userGSTINTransin': vehicle.get("userGSTINTransin"),
                    'get_veh_enteredDate': vehicle.get("enteredDate"),
                    'get_veh_transMode': vehicle.get("transMode"),
                    'get_veh_transDocNo': vehicle.get("transDocNo"),
                    'get_veh_transDocDate': vehicle.get("transDocDate"),
                    'get_veh_groupNo': vehicle.get("groupNo"),
                }))

            rec.vehicles_id = vehicle_vals
            self.get_eway_generate_qr_code()
            self.get_eway_generate_barcode()

    # clear the Fields
    def clear_the_field(self):
        for rec in self:
            # ewb details
            rec.get_ewbNo = False
            rec.get_ewayBillDate = False
            rec.get_genMode = False
            rec.get_userGstin = False
            rec.get_noValidDays = False
            rec.get_validUpto = False

            # transaction details
            rec.get_supplyType = False
            rec.get_subSupplyType = False
            rec.get_docType = False
            rec.get_transactionType = False
            rec.get_vehicleType = False

            # bill from details
            rec.get_billfrom_Gstin = False
            rec.get_billfrom_TrdName = False
            rec.get_billfrom_state = False

            # Dispatch From Details
            rec.get_dispatch_fromAddr1 = False
            rec.get_dispatch_fromAddr2 = False
            rec.get_dispatch_fromPlace = False
            rec.get_dispatch_fromPincode = False
            rec.get_dispatch_actFromStateCode = False
            rec.get_dispatch_fromStateCode = False

            # Bill to details
            rec.get_billto_Gstin = False
            rec.get_billto_TrdName = False
            rec.get_billto_StateCode = False

            # Ship to Details
            rec.get_shipto_Addr1 = False
            rec.get_shipto_Addr2 = False
            rec.get_shipto_Place = False
            rec.get_shipto_Pincode = False
            rec.get_actToStateCode = False
            rec.get_shipto_StateCode = False

            # document details
            rec.get_transporterId = False
            rec.get_transporterName = False
            rec.get_docNo = False
            rec.get_docDate = False
            rec.get_actualDist = False

            # total values
            rec.get_cgstValue = False
            rec.get_sgstValue = False
            rec.get_igstValue = False
            rec.get_cessValue = False
            rec.get_otherValue = False
            rec.get_cessNonAdvolValue = False
            rec.get_totalValue = False
            rec.get_totInvValue = False

            # other details
            rec.get_status = False
            rec.get_extendedTimes = False
            rec.get_rejectStatus = False
            rec.get_ewbNo_json = False

            # products
            rec.products_id.get_eway_hsnCode = False
            rec.products_id.get_eway_productName = False
            rec.products_id.get_eway_productDesc = False
            rec.products_id.get_eway_quantity = False
            rec.products_id.get_eway_qtyUnit = False
            rec.products_id.get_eway_cgstRate = False
            rec.products_id.get_eway_sgstRate = False
            rec.products_id.get_eway_igstRate = False
            rec.products_id.get_eway_cessRate = False
            rec.products_id.get_eway_cessNonAdvol = False
            rec.products_id.get_eway_taxableAmount = False

            # vehicles
            rec.vehicles_id.get_veh_updMode = False
            rec.vehicles_id.get_veh_updMode = False
            rec.vehicles_id.get_veh_vehicleNo = False
            rec.vehicles_id.get_veh_fromPlace = False
            rec.vehicles_id.get_veh_fromState = False
            rec.vehicles_id.get_veh_tripshtNo = False
            rec.vehicles_id.get_veh_userGSTINTransin = False
            rec.vehicles_id.get_veh_enteredDate = False
            rec.vehicles_id.get_veh_transMode = False
            rec.vehicles_id.get_veh_transDocNo = False
            rec.vehicles_id.get_veh_transDocDate = False
            rec.vehicles_id.get_veh_groupNo = False

            # QR code and Barcode
            rec.get_eway_barcode = False
            rec.get_eway_qr_code = False

    # E-Way Bill Generate QR Code
    @api.depends('get_ewbNo', 'get_userGstin', 'get_ewayBillDate')
    def get_eway_generate_qr_code(self):
            for rec in self:
                qr = qrcode.QRCode(version=1,error_correction=qrcode.constants.ERROR_CORRECT_L,box_size=3,border=4,)
                # Format the date correctly for the QR code
                eway_date_str = rec.get_ewayBillDate
                if eway_date_str:
                    # Construct the data string for the QR code including additional fields
                    qr_data = f"{rec.get_ewbNo}/{rec.get_userGstin}/{eway_date_str}"
                    qr.add_data(qr_data)
                    qr.make(fit=True)
                    img = qr.make_image()
                    temp = BytesIO()
                    img.save(temp, format="PNG")
                    qr_image = base64.b64encode(temp.getvalue())
                    rec.get_eway_qr_code = qr_image

    # E-Way Bill  Generate Barcode
    @api.depends('get_ewbNo')
    def get_eway_generate_barcode(self):
            for rec in self:
                if rec.get_ewbNo:
                    barcode_param = rec.get_ewbNo
                    barcode_bytes = io.BytesIO()
                    barcode = code128.image(barcode_param, height=80).save(barcode_bytes, "PNG")
                    barcode_bytes.seek(0)
                    image_data = base64.b64encode(barcode_bytes.read()).decode('utf-8')
                    rec.get_eway_barcode = image_data

    # Download the Active Eway Bill PDF and Cancelled Eway Bill PDF
    def action_print_eway_bill(self):
        self.ensure_one()
        if self.get_status == 'ACT':
            return self.env.ref('consolidate_eway_bill_addons.action_active_eway_bill_pdf').report_action(self)
        elif self.get_status == 'CNL':
            return self.env.ref('consolidate_eway_bill_addons.action_cancelled_eway_bill_pdf').report_action(self)
        else:
            raise UserError('Unknown E-way Bill Status.')




















