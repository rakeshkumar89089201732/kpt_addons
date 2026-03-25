# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Compatibility alias for views that might reference invoice_policy instead of default_invoice_policy
    invoice_policy = fields.Selection(
        selection=[
            ('order', "Invoice what is ordered"),
            ('delivery', "Invoice what is delivered")
        ],
        string="Invoicing Policy (Legacy)",
        config_parameter='sale.default_invoice_policy',
        help="Legacy field name for default_invoice_policy. Use default_invoice_policy instead.")
