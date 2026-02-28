import base64
import json
from io import BytesIO
import io
from barcode import EAN13
from barcode.writer import ImageWriter
import code128
import qrcode
from odoo import fields, models, api, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    # part b creation fields............................................................................................
    partb_id = fields.One2many(comodel_name='partb', inverse_name='invoice_no', string='PartB Id')
    part_b = fields.Boolean(string='Enable Part B')
    vehicle_no = fields.Char(string='vehicleNo')
    from_place = fields.Char(string='fromPlace')
    fromState = fields.Many2one('res.country.state', string="fromState", store=True)
    reason_codes = fields.Selection([('1', 'Due to Break Down'),
                                     ('2', 'Due to Transshipment'),
                                     ('3', 'Others (Pls. Specify)'),
                                     ('4', 'First Time')], string='Reason Codes')
    reason_remarks = fields.Char(string='Reason Remarks')
    trans_doc_no = fields.Char(string="transDocNo")
    trans_doc_date = fields.Date(string="transDocDate")
    transportation_mode = fields.Selection([('1','Road'),
                                            ('2', 'Rail'),
                                            ('3', 'Air'),
                                            ('4', 'Ship or Ship Cum Road/Rail'),
                                            ('5', 'inTransit')
                                            ],string='Transportation Mode')
    vehicle_type = fields.Selection([('R','Regular'),
                                                 ('O',	'ODC(Over Dimentional Cargo)')],
                                                  string='Vehicle Type')
    # Initiate Multi vehicle fields.....................................................................................
    initiate_vehicle_id = fields.One2many(comodel_name='initiate.multivehicle', inverse_name='invoice_no', string='Initiate Multi Vehicle')
    initiate_multi_vehicle = fields.Boolean(string="Enable Initiate Multi Vehicle", store=True, default=False)
    initiate_ewb_no = fields.Char(string="ewbNo", related='eway_no', store=True)
    initiate_from_place = fields.Char(string="From Place", store=True)
    initiate_from_state = fields.Many2one('res.country.state', string="From State", store=True)
    initiate_to_place = fields.Char(string="To Place", store=True)
    initiate_to_state = fields.Many2one('res.country.state', string="To State", store=True)
    initiate_reason = fields.Selection([
        ('1', 'Break Down'),
        ('2', 'Transhipment'),
        ('3', 'Others')], string="Reason", store=True)
    initiate_reason_remarks = fields.Char(string="Reason Remarks", store=True)
    initiate_total_quantity = fields.Integer(string="Total Quantity", store=True)
    initiate_unit_code = fields.Selection([
        ('BAG', 'Bags'),
        ('BAL', 'Bale'),
        ('BDL', 'Bundles'),
        ('BKL', 'Buckles'),
        ('BOU', 'Billion of Units'),
        ('BOX', 'Box'),
        ('BTL', 'Bottles'),
        ('BUN', 'Bunches'),
        ('CAN', 'Cans'),
        ('CBM', 'Cubic Meters'),
        ('CCM', 'Cubic Centimeters'),
        ('CMS', 'Centimeters'),
        ('CTN', 'Cartons'),
        ('DOZ', 'Dozens'),
        ('DRM', 'Drums'),
        ('GGK', 'Great Gross'),
        ('GMS', 'Grammes'),
        ('GRS', 'Gross'),
        ('GYD', 'Gross Yards'),
        ('KGS', 'Kilograms'),
        ('KLR', 'Kilolitre'),
        ('KME', 'Kilometre'),
        ('LTR', 'Litres'),
        ('MTR', 'Meters'),
        ('MLT', 'Millilitre'),
        ('MTS', 'Metric Ton'),
        ('NOS', 'Numbers'),
        ('OTH', 'Others'),
        ('PAC', 'Packs'),
        ('PCS', 'Pieces'),
        ('PRS', 'Pairs'),
        ('QTL', 'Quintal'),
        ('ROL', 'Rolls'),
        ('SET', 'Sets'),
        ('SQF', 'Square Feet'),
        ('SQM', 'Square Meters'),
        ('SQY', 'Square Yards'),
        ('TBS', 'Tablets'),
        ('TGM', 'Ten Gross'),
        ('THD', 'Thousands'),
        ('TON', 'Tonnes'),
        ('TUB', 'Tubes'),
        ('UGS', 'US Gallons'),
        ('UNT', 'Units'),
        ('YDS', 'Yards')], string="Unit")
    initiate_mode_of_transport = fields.Selection([
        ("1", "By Road"),
        ("2", "Rail"),
        ("3", "Air"),
        ("4", "Ship or Ship Cum Road/Rail"),
        ("5", "inTransit")],
        string="transMode", tracking=True)
    # Add Multi vehicle Fields..........................................................................................
    add_multivehicle = fields.Boolean(string="Enable Add Multivehicle")
    add_multivehicle_id = fields.One2many(comodel_name='add.multivehicle', inverse_name='invoice_no', string='add_multivehicle_id')
    initiate_group_id = fields.Many2one(comodel_name='initiate.multivehicle', string='Initiate Group Name', domain="[('veh_ewb_no', '=', add_multi_eway_no)]")
    add_multi_eway_no = fields.Char(related='eway_no', string='E-Way No')
    add_multi_vehicle_no = fields.Char(string="Vehicle No")
    add_multi_group_no = fields.Char(string="Group No", related='initiate_group_id.initiate_group_no')
    add_multi_trans_doc_no = fields.Char(string="Vehicle Trans Doc No")
    add_multi_trans_doc_date = fields.Date(string="Vehicle Trans Doc Date")
    add_multi_quantity = fields.Integer(string='Quantity', related='initiate_group_id.veh_total_quantity')
    # Change Multi Vehicle fields.......................................................................................
    update_multivehicle = fields.Boolean(string="Enable Update Multivehicle")
    update_eway_no = fields.Char(related='eway_no', string='E-Way No')
    update_group_name = fields.Many2one(comodel_name='initiate.multivehicle', string='Initiate Group Name',
                                        domain="[('veh_ewb_no', '=', update_eway_no)]")
    update_group_no = fields.Char(string="Group No", related='update_group_name.initiate_group_no')
    update_old_veh_no = fields.Many2one(comodel_name='add.multivehicle', string="Old Vehicle No", domain="[('initiate_id', '=', update_group_name)]")
    update_new_vehicle_no = fields.Char(string="New Vehicle No")
    update_old_trans_doc_no = fields.Char(string="Old Trans Doc No", related='update_old_veh_no.transDocNo')
    update_new_trans_doc_no = fields.Char(string="New Trans Doc No")
    update_from_place = fields.Char(string="From Place")
    update_from_state = fields.Many2one('res.country.state', string="From State", store=True)
    update_reason_code = fields.Selection([
        ('1', 'Due to Break Down'),
        ('2', 'Due to Transshipment'),
        ('3', 'Others (Pls. Specify)'),
        ('4', 'First Time')], string="Reason", store=True)
    update_reason_remarks = fields.Char(string="Reason Remarks", store=True)
    change_vehicle_id = fields.One2many(comodel_name='change.multivehicle', inverse_name='change_invoice_no', string='Change Vehicle')
    #part-B jason qr code and barcode details...........................................................................
    part_b_eway_bill_no = fields.Char(string="ewayBillNo", readonly=True)
    part_b_generated_date = fields.Char(string="ewayBillDate", readonly=True)
    part_b_generated_by = fields.Char(string="userGstin", readonly=True)
    part_b_valid_date = fields.Char(string="validUpto", readonly=True)
    part_b_qr_code = fields.Binary(string='QR Code', readonly=True)
    part_b_barcode = fields.Binary(string='Barcode', readonly=True)

    # Part-B ........................................................................................................
    def create_partb(self):
        return self.env['mastergst.edi']._generate_partb(self)

    # Generate the Part-B Details(part_b_eway_bill_no, part_b_generated_date, part_b_generated_by, part_b_valid_date)
    def print_partb_ewaybill_data(self):
        for record in self:
            ewaybill_data = None
            dynamic_part = f"{record.name}_Final_Part_B_JSON"
            ewaybill_file_pattern = dynamic_part
            if record.attachment_ids:
                for attachment in record.attachment_ids:
                    if attachment.name and attachment.name.endswith(dynamic_part):
                        if attachment.datas:
                            try:
                                ewaybill_data = base64.b64decode(attachment.datas).decode('utf-8')
                            except Exception as decode_error:
                                print(f"Error decoding base64 data: {decode_error}")
                        break
            if ewaybill_data:
                try:
                    ewaybill_json = json.loads(ewaybill_data)
                    record.part_b_eway_bill_no = ewaybill_json.get('data', {}).get("ewbNo")
                    record.part_b_generated_date = ewaybill_json.get('data', {}).get("ewayBillDate")
                    record.part_b_generated_by = ewaybill_json.get('data', {}).get("fromGstin")
                    record.part_b_valid_date = ewaybill_json.get('data', {}).get("validUpto")
                    self.partb_generate_qr_code()
                    self.partb_generate_barcode()
                except json.JSONDecodeError:
                    print('Error decoding JSON data from the file.')
                except ValueError as e:
                    print(f'Error parsing value: {e}')
            else:
                print(f'E-way Bill JSON file matching pattern {ewaybill_file_pattern} not found.')

        return True

        # Part-B Generate QR Code(part_b_qr_code)

    # Generate the Part-B QR code(part_b_qr_code)
    @api.depends('part_b_eway_bill_no', 'part_b_generated_by', 'part_b_generated_date')
    def partb_generate_qr_code(self):
        for rec in self:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=3,
                border=4,
            )
            # Format the date correctly for the QR code
            eway_date_str = rec.part_b_generated_date

            if eway_date_str:
                # Construct the data string for the QR code including additional fields
                qr_data = f"{rec.part_b_eway_bill_no}/{rec.part_b_generated_by}/{eway_date_str}"
                qr.add_data(qr_data)
                qr.make(fit=True)
                img = qr.make_image()
                temp = BytesIO()
                img.save(temp, format="PNG")
                qr_image = base64.b64encode(temp.getvalue())
                rec.part_b_qr_code = qr_image
                print(rec.part_b_qr_code)
                if rec.part_b:
                    domain = [
                        ('invoice_no', '=', self.id),
                        ('ewbNo', '=', self.part_b_eway_bill_no),
                        ('vehicleNo', '=', self.vehicle_no),
                        ('transDocNo', '=', self.trans_doc_no),
                        ('transDocDate', '=', self.trans_doc_date),
                        ('vehAddedDate', '=', self.part_b_generated_date),
                        ('vehicle_mode', '=', self.transportation_mode),
                        ('state', '=', 'post'),
                    ]
                    existing = self.env['add.multivehicle'].search(domain, limit=1)
                    if not existing:
                        record = {
                            "invoice_no": self.id,
                            "ewbNo": self.part_b_eway_bill_no,
                            "groupNo": 0,
                            "quantity": 0,
                            "from_place": self.dispatch_from.city,
                            "vehicleNo": self.vehicle_no,
                            "transDocNo": self.trans_doc_no,
                            "transDocDate": self.trans_doc_date,
                            "vehAddedDate": self.part_b_generated_date,
                            "vehicle_mode": self.transportation_mode,
                            "state": 'post'
                        }
                        self.env['add.multivehicle'].create(record)

    # Part-B Generate Barcode(part_b_barcode)
    @api.depends('part_b_eway_bill_no')
    def partb_generate_barcode(self):
        for rec in self:
            if rec.part_b_eway_bill_no:
                barcode_param = rec.part_b_eway_bill_no
                barcode_bytes = io.BytesIO()
                barcode = code128.image(barcode_param, height=80).save(barcode_bytes, "PNG")
                barcode_bytes.seek(0)
                image_data = base64.b64encode(barcode_bytes.read()).decode('utf-8')
                rec.part_b_barcode = image_data

    # Download the Part-B PDF
    def print_part_b_pdf(self):
        self.print_partb_ewaybill_data()
        self.partb_generate_barcode()
        self.partb_generate_qr_code()
        return self.env.ref('mastergst_addons.action_part_b_eway_bill').report_action(self)

    def cancelled_partb_pdf(self):
        self.print_ewaybill_cancel_data()
        return self.env.ref('mastergst_addons.action_cancel_part_b_eway_bill').report_action(self)

    # Initiate Multivehicle.............................................................................................

    # Send Initiate multivehicle request in E-Way bill portal
    def initiate_multivehicle(self):
        return self.env['mastergst.edi']._initiate_multivehicle(self)

    # Make empty on initiate multivehicle fields
    def clear_initiate_multivehicle_fields(self):
        for rec in self:
            rec.initiate_from_place = False
            rec.initiate_from_state = False
            rec.initiate_to_place = False
            rec.initiate_to_state = False
            rec.initiate_reason = False
            rec.initiate_reason_remarks = False
            rec.initiate_total_quantity = False
            rec.initiate_unit_code = False
            rec.initiate_mode_of_transport = False

    # Add Multivehicle..................................................................................................

    # Send Add Multivehicle Request in E-Way bill portal
    def add_multivehicle_creation(self):
        return self.env['mastergst.edi']._generate_add_multivehicle(self)

    # Make empty on Add multivehicle fields
    def clear_add_multivehicle_fields(self):
        for rec in self:
            rec.add_multi_vehicle_no = False
            rec.add_multi_group_no = False
            rec.add_multi_trans_doc_no = False
            rec.add_multi_trans_doc_date = False
            rec.add_multi_quantity = False

    # Create a record in Add Multivehicle
    def print_ewaybill_data(self):
        res = super().print_ewaybill_data()
        # Prepare search domain to check if record already exists
        if not self.enable_parta_slip:
            domain = [
                ('invoice_no', '=', self.id),
                ('ewbNo', '=', self.eway_no),
                ('vehicleNo', '=', self.transport_vehicle_no),
                ('transDocNo', '=', self.transportation_doc),
                ('transDocDate', '=', self.transportation_doc_date),
                ('vehAddedDate', '=', self.eway_date),
                ('vehicle_mode', '=', self.transport_mode2 if self.transport_mode2 else self.transport_mode3),
                ('state', '=', 'post'),
            ]
            existing = self.env['add.multivehicle'].search(domain, limit=1)
            if not existing:
                record = {
                    "invoice_no": self.id,
                    "ewbNo": self.eway_no,
                    "groupNo": 0,
                    "quantity": 0,
                    "from_place": self.dispatch_from.city,
                    "vehicleNo": self.transport_vehicle_no,
                    "transDocNo": self.transportation_doc,
                    "transDocDate": self.transportation_doc_date,
                    "vehAddedDate": self.eway_date,
                    "vehicle_mode": self.transport_mode2 if self.transport_mode2 else self.transport_mode3,
                    "state": 'post'
                }
                self.env['add.multivehicle'].create(record)
        return res

    # Download the Multivehicle PDF
    def print_multivehicle_pdf(self):
        self.print_ewaybill_data()
        self.generate_qr_code()
        self._generate_barcode()
        return self.env.ref('mastergst_addons.action_multivehicle_eway_bill').report_action(self)

    def download_cancel_multivehicle_pdf(self):
        self.print_ewaybill_cancel_data()
        return self.env.ref('mastergst_addons.action_cancel_multivehicle_eway_bill').report_action(self)

    # Change Multivehicle...............................................................................................

    # Send Change Multivehicle Request to E-Way bill portal
    def change_multivehicle(self):
        return self.env['mastergst.edi']._change_multivehicle(self)

    # Make empty change multivehicle field
    def clear_change_multivehicle(self):
        for rec in self:
            rec.update_group_name = False
            rec.update_group_no = False
            rec.update_old_veh_no = False
            rec.update_new_vehicle_no = False
            rec.update_old_trans_doc_no = False
            rec.update_new_trans_doc_no = False
            rec.update_from_place = False
            rec.update_from_state = False
            rec.update_reason_code = False
            rec.update_reason_remarks = False

    def create_partb_record_without_transporter(self):
            if not self.enable_parta_slip:
                domain = [
                    ('invoice_no', '=', self.id),
                    ('eway_no', '=', self.eway_no),
                    ('ewaybilldate', '=', self.eway_date),
                    ('veupddate', '=', self.eway_date),
                    ('vehileno', '=', self.transport_vehicle_no),
                    ('fromplace', '=', self.dispatch_from.city),
                    ('fromstate', '=', self.dispatch_from.state_id.id),
                    ('transdocno', '=', self.transportation_doc),
                    ('transdocdate', '=', self.transportation_doc_date),
                    ('transmode', '=', self.transport_mode2 if self.transport_mode2 else self.transport_mode3),
                    ('state', '=', 'post'),
                ]
                existing = self.env['partb'].search(domain, limit=1)
                if not existing:
                    record = {
                        "invoice_no": self.id,
                        "eway_no": self.eway_no,
                        "ewaybilldate": self.eway_date,
                        "veupddate": self.eway_date,
                        "vehileno": self.transport_vehicle_no,
                        "fromplace": self.dispatch_from.city,
                        "fromstate": self.dispatch_from.state_id.id,
                        "transdocno": self.transportation_doc,
                        "transdocdate": self.transportation_doc_date,
                        "transmode": self.transport_mode2 if self.transport_mode2 else self.transport_mode3,
                        "state": 'post'
                    }
                    self.env['partb'].create(record)



































































