# -*- coding: utf-8 -*-

from odoo import models, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_print_with_copies(self, report_xml_id):
        """Open wizard to select number of copies for printing"""
        self.ensure_one()
        
        report_action = self.env.ref(report_xml_id)
        
        return {
            'name': 'Select Number of Copies',
            'type': 'ir.actions.act_window',
            'res_model': 'print.copy.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_report_action_id': report_action.id,
                'default_record_ids': str(self.ids),
                'default_model_name': self._name,
            }
        }
    
    def action_print_purchase_order_copies(self):
        return self.action_print_with_copies('sale_order_extension.action_report_kpt_purchase')
