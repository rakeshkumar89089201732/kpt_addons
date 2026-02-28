from odoo import models,api, fields, _

class PartB(models.Model):
    _name = 'partb'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'veupddate desc'

    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', 'Created By', default=lambda self: self.env.user)
    created_date = fields.Datetime(string='Created On', readonly=True, index=True, default=fields.Datetime.now)
    invoice_no = fields.Many2one(comodel_name='account.move', string='Invoice No')
    name = fields.Char(string='name', related='invoice_no.name')
    # entereddate = fields.Char(string='enteredDate')
    eway_no = fields.Char(string='ewbNo')
    ewaybilldate =fields.Char(string='ewayBillDate')
    veupddate = fields.Char(string='vehUpdDate')
    vehileno = fields.Char(string='vehicleNo')
    fromplace = fields.Char(string='fromPlace')
    fromstate = fields.Many2one(comodel_name='res.country.state', string='fromState')
    reasoncode = fields.Selection([('1', 'Due to Break Down'),
                                     ('2', 'Due to Transshipment'),
                                     ('3', 'Others (Pls. Specify)'),
                                     ('4', 'First Time')], string='reasonCode')
    reasonrem = fields.Char(string='reasonRem')
    transdocno = fields.Char(string='transDocNo')
    transdocdate = fields.Char(string='transDocDate')
    transmode = fields.Selection([('1','Road'),
                                            ('2', 'Rail'),
                                            ('3', 'Air'),
                                            ('4', 'Ship or Ship Cum Road/Rail'),
                                            ('5', 'inTransit')
                                            ],string='transMode')
    state = fields.Selection([('post', 'Posted'), ('cancel', 'Cancelled')], string='state')