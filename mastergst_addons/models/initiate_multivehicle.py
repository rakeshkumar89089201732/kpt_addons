from odoo import models, api, fields, _
from odoo.exceptions import ValidationError

class InitiateMultivehicle(models.Model):
    _name = 'initiate.multivehicle'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", index=True, default='New', compute='compute_name')
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', 'Created By', default=lambda self: self.env.user)
    created_date = fields.Datetime(string='Created On', readonly=True, index=True, default=fields.Datetime.now)
    invoice_no = fields.Many2one(comodel_name='account.move', string="Invoice No")
    veh_ewb_no = fields.Char(string="ewbNo")
    veh_from_place = fields.Char(string="From Place")
    veh_from_state = fields.Many2one(comodel_name='res.country.state', string="From State")
    veh_to_place = fields.Char(string="To Place")
    veh_to_state = fields.Many2one(comodel_name='res.country.state', string="To State")
    veh_reason = fields.Selection([
        ('1', 'Due to Break Down'),
        ('2', 'Due to Transshipment'),
        ('3', 'Others (Pls. Specify)'),
        ('4', 'First Time')], string="Reason", store=True)
    veh_reason_remarks = fields.Char(string="Reason Remarks")
    veh_total_quantity = fields.Integer(string="Total Quantity", store=True)
    veh_unit_code = fields.Selection([
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
    veh_mode_of_transport = fields.Selection([
        ("1", "By Road"),
        ("2", "Rail"),
        ("3", "Air"),
        ("4", "Ship or Ship Cum Road/Rail"),
        ("5", "inTransit")],
        string="transMode", tracking=True)
    state = fields.Selection([('draft', 'Draft'),
                                          ('post', 'Posted'),
                                          ('cancel', 'Cancelled')], string="Status")
    initiate_group_no = fields.Char(string="groupNo")
    initiate_created_date = fields.Char(string="createdDate")


    @api.depends('veh_from_place', 'veh_to_place', 'veh_total_quantity', 'veh_unit_code')
    def compute_name(self):
        for rec in self:
            quantity = float(rec.veh_total_quantity)
            rec.name = f"{rec.veh_from_place} - {rec.veh_to_place}, {quantity} {rec.veh_unit_code}"

    @api.model
    def create(self, vals):
        domain = [
            ('veh_ewb_no', '=', vals.get('veh_ewb_no')),
            ('veh_from_place', '=', vals.get('veh_from_place')),
            ('veh_to_place', '=', vals.get('veh_to_place')),
            ('veh_total_quantity', '=', vals.get('veh_total_quantity')),
            ('veh_unit_code', '=', vals.get('veh_unit_code')),
        ]
        existing = self.search(domain, limit=1)
        if existing:
            raise ValidationError(
                _('A Initiate Multivehicle with the same EWB No, From Place, To Place, Total Quantity, and Unit Code is already exists. Check the values'))

        return super(InitiateMultivehicle, self).create(vals)
