from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_revoke_to_draft(self):
        for record in self:
            record.write({'state': 'draft'})
            record.message_post(body="Order manually revoked to Draft state by user.")

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_revoke_to_draft(self):
        for record in self:
            record.write({'state': 'draft'})
            record.message_post(body="Order manually revoked to Draft state by user.")

class RepairOrder(models.Model):
    _inherit = 'repair.order'

    def action_revoke_to_draft(self):
        for record in self:
            record.write({'state': 'draft'})
            record.message_post(body="Repair Order manually revoked to Draft state by user.")

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_revoke_to_draft(self):
        for record in self:
            record.write({'state': 'draft'})
            # Also try to set moves to draft? Use with caution.
            # record.move_ids.write({'state': 'draft'}) 
            # Keeping it simple: just picking state allows form edit often, 
            # but moves might be locked. 
            # If user wants to "revoke", usually implies full reset. 
            # But changing Done stock moves is dangerous. 
            # We will just change picking state to allow UI edits if that's the goal.
            record.message_post(body="Picking manually revoked to Draft state by user.")
