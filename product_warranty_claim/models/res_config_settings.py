# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auto_create_warranty_invoice = fields.Boolean(
        string='Auto-create Invoice for Paid Warranties',
        config_parameter='product_warranty_claim.auto_create_warranty_invoice',
        default=False,
        help='Automatically create invoices when paid warranties are generated from sales orders'
    )
