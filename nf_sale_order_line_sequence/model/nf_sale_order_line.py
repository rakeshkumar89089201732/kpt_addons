# -*- coding: utf-8 -*-
# Copyright (C) 2021-Today: Part of NextFlowIT. 
# @author:  Part of NextFlowIT. 

from odoo import models, fields, api

class NfSaleOrderLineNumber(models.Model):
    _inherit='sale.order.line'

    nf_number = fields.Integer(compute="compute_sale_order_line_sequence", string="No.")

    @api.depends('order_id')
    def compute_sale_order_line_sequence(self):    
        self.nf_number = 0
        sale_order_line_count=0
        for sale_order_line_number in self.order_id.order_line:
            sale_order_line_count += 1
            sale_order_line_number.nf_number = sale_order_line_count          
       