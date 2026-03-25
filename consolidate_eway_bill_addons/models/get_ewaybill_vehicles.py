from odoo import models, api, fields, _

class GetEwaybillVehicles(models.Model):
    _name = 'get.ewaybill.vehicles'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'get_veh_enteredDate desc'

    name = fields.Char(string='Name', related='get_veh_vehicleNo')
    vehicles_ids = fields.Many2one(comodel_name='get.ewaybill', string='Vehicles Id')
    get_veh_updMode =  fields.Char(string='updMode')
    get_veh_vehicleNo = fields.Char(string="vehicleNo")
    get_veh_fromPlace = fields.Char(string="fromPlace")
    get_veh_fromState = fields.Many2one(string="fromState", comodel_name='res.country.state')
    get_veh_tripshtNo = fields.Char(string="tripshtNo")
    get_veh_userGSTINTransin = fields.Char(string="userGSTINTransin")
    get_veh_enteredDate = fields.Char(string="enteredDate")
    get_veh_transMode = fields.Selection([
        ("1", "By Road"),
        ("2", "Rail"),
        ("3", "Air"),
        ("4", "Ship or Ship Cum Road/Rail")
    ],string="Transportation Mode")
    get_veh_transDocNo = fields.Char(string="transDocNo")
    get_veh_transDocDate = fields.Char(string="transDocDate")
    get_veh_groupNo = fields.Integer(string="GroupNo")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', 'Created By', default=lambda self: self.env.user)
    created_date = fields.Datetime(string='Created On', readonly=True, index=True, default=fields.Datetime.now)