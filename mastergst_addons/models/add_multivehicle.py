from odoo import models, api, fields, _
from odoo.exceptions import ValidationError

class AddMultivehicle(models.Model):
    _name = 'add.multivehicle'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'vehAddedDate desc'

    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', 'Created By', default=lambda self: self.env.user)
    created_date = fields.Datetime(string='Created On', readonly=True, index=True, default=fields.Datetime.now)
    invoice_no = fields.Many2one(comodel_name='account.move', string='Invoice')
    initiate_id = fields.Many2one(comodel_name='initiate.multivehicle', string='Initiate Group Name')
    name = fields.Char(string='Name',  related='vehicleNo')
    from_place = fields.Char(string='fromplace')
    ewbNo = fields.Char(string='ewbNo')
    vehicleNo = fields.Char(string='vehicleNo')
    groupNo = fields.Char(string='groupNo', related='initiate_id.initiate_group_no')
    transDocNo = fields.Char(string='transDocNo')
    transDocDate = fields.Char(string='transDocDate')
    quantity = fields.Integer(string='quantity')
    vehAddedDate = fields.Char(string='vehAddedDate')
    state = fields.Selection([('post', 'Posted'), ('cancel', 'Cancelled')], string='State')
    vehicle_mode = fields.Selection([
        ("1", "By Road"),
        ("2", "Rail"),
        ("3", "Air"),
        ("4", "Ship or Ship Cum Road/Rail"),
        ("5", "inTransit")],
        string="transMode", tracking=True)

    @api.model
    def create(self, vals):
        domain = [
            ('initiate_id', '=', vals.get('initiate_id')),
            ('ewbNo', '=', vals.get('ewbNo')),
            ('vehicleNo', '=', vals.get('vehicleNo')),
            ('groupNo', '=', vals.get('groupNo')),
        ]
        existing = self.search(domain, limit=1)
        if existing:
            raise ValidationError(
                _('A Add Multivehicle with the same Initiate Group name,  ewbNo, vehicleNo, and groupNo is already exists. Check the values'))
        return super(AddMultivehicle, self).create(vals)

