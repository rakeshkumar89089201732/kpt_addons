from odoo import api, models, fields, tools


class Company(models.Model):
    _inherit = 'res.company'


    bsr_code = fields.Char('BSR Code')
