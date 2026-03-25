# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Using Odoo's built-in cash rounding feature
    # No need for custom round_off_account_id
