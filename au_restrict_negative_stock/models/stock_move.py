from odoo import models, _
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = "stock.move"

    def _action_done(self, cancel_backorder=False):
        for move in self:
            product = move.product_id

            # Skip non-stockable (consumable, service)
            if product.type != 'product':
                continue

            # Check exceptions
            if (product.allow_negative_stock or
                product.categ_id.allow_negative_stock or
                move.location_id.allow_negative_stock or
                move.location_dest_id.allow_negative_stock):
                continue

            # Available stock
            qty_on_hand = product.with_context(location=move.location_id.id).qty_available
            if qty_on_hand < move.product_uom_qty:
                raise UserError(_(
                    "Operation not allowed!\n\n"
                    "Product: %s\n"
                    "Available: %.2f %s\n"
                    "Required: %.2f %s\n\n"
                    "This move would cause negative stock."
                ) % (
                    product.display_name,
                    qty_on_hand, product.uom_id.name,
                    move.product_uom_qty, product.uom_id.name
                ))

        return super()._action_done(cancel_backorder=cancel_backorder)
