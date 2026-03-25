# -*- coding: utf-8 -*-
from odoo import models, fields, api,_
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _prepare_report_data(self):

        xml_id = 'sale_order_discount_approval_odoo.action_report_product_product'
        data = {
            "object": self
        }
        return xml_id, data

    def process_printing_data(self):
        self.ensure_one()
        return self.env.ref('sale_order_discount_approval_odoo.action_report_product_product').report_action(self)
