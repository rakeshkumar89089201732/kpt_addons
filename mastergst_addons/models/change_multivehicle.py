from odoo import models, api, fields, _

class ChangeMultivehicle(models.Model):
    _name = 'change.multivehicle'

    name = fields.Char(string='Name', compute='compute_name')
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', 'Created By', default=lambda self: self.env.user)
    created_date = fields.Datetime(string='Created On', readonly=True, index=True, default=fields.Datetime.now)
    change_invoice_no = fields.Many2one(comodel_name='account.move', string='Invoice No')
    change_ewbNo = fields.Char(string='ewbNo')
    change_group_name = fields.Many2one(comodel_name='initiate.multivehicle', string='Group name')
    change_groupNo = fields.Char(string='groupNo', related='change_group_name.initiate_group_no')
    change_vehUpdDate = fields.Char(string='vehUpdDate')
    change_old_vehno = fields.Char(string='OldVehno')
    change_new_vehno = fields.Char(string='NewVehno')
    change_old_docno = fields.Char(string='OldDocNo')
    change_new_docno = fields.Char(string='NewDocNo')
    change_from_place = fields.Char(string='fromplace')
    change_from_state = fields.Many2one(string='fromstate', comodel_name='res.country.state')
    change_reason =  fields.Selection([
        ('1', 'Due to Break Down'),
        ('2', 'Due to Transshipment'),
        ('3', 'Others (Pls. Specify)'),
        ('4', 'First Time')], string="Reason", store=True)
    change_remarks = fields.Char(string='Change Remarks')
    state = fields.Selection([('post', 'Posted'), ('cancel', 'Cancelled')], string='state')

    @api.depends('change_new_vehno', 'change_invoice_no')
    def compute_name(self):
        for rec in self:
            rec.name = f"{rec.change_new_vehno} - {rec.change_invoice_no.name}"



