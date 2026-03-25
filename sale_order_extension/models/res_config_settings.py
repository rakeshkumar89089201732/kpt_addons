# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    # Using Odoo's built-in cash rounding feature
    # Configuration is done via Accounting > Configuration > Cash Roundings
