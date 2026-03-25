# -*- coding: utf-8 -*-
from odoo import models, fields

class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    ifsc_code = fields.Char('IFSC Code')
    swift_code = fields.Char('SWIFT Code')