# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    tan_number = fields.Char(
        string='TAN Number',
        size=10,
        help='Tax Deduction and Collection Account Number used for TDS compliance.'
    )
