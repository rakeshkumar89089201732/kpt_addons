from odoo import api, fields, models, _


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_voucher_type(self):
        """Determine voucher type based on picking type and operation"""
        self.ensure_one()
        
        if not self.picking_id:
            return 'stock_journal'
        
        picking = self.picking_id
        picking_type = picking.picking_type_id
        
        if picking_type.code == 'incoming':
            if picking.origin and 'Return' in picking.origin:
                return 'purchase_return'
            return 'purchase'
        elif picking_type.code == 'outgoing':
            if picking.origin and 'Return' in picking.origin:
                return 'sales_return'
            return 'sales'
        elif picking_type.code == 'internal':
            return 'internal'
        elif picking_type.code == 'mrp_operation':
            return 'manufacturing'
        else:
            return 'stock_journal'
    
    def _get_particulars(self):
        """Get partner name or description for the ledger entry"""
        self.ensure_one()
        
        if self.partner_id:
            return self.partner_id.name
        elif self.picking_id and self.picking_id.partner_id:
            return self.picking_id.partner_id.name
        elif self.picking_id:
            return self.picking_id.name
        else:
            return self.reference or self.name
    
    def _create_stock_ledger_entry(self):
        """Create stock ledger entry for this move"""
        for move in self:
            if move.state != 'done':
                continue
            
            # Skip if not a valuation move
            if not move.product_id.valuation == 'real_time':
                continue
            
            # Get source and destination location types
            src_usage = move.location_id.usage
            dest_usage = move.location_dest_id.usage
            
            # Only create ledger for moves involving internal locations
            if src_usage not in ['internal', 'transit'] and dest_usage not in ['internal', 'transit']:
                continue
            
            # Get valuation
            valuation = 0.0
            if move.stock_valuation_layer_ids:
                valuation = sum(move.stock_valuation_layer_ids.mapped('value'))
            else:
                valuation = move.product_qty * move.product_id.standard_price
            
            # Determine inward/outward based on location
            inward_qty = 0.0
            inward_value = 0.0
            outward_qty = 0.0
            outward_value = 0.0
            
            if dest_usage == 'internal' and src_usage != 'internal':
                # Incoming to internal location
                inward_qty = move.product_qty
                inward_value = abs(valuation)
            elif src_usage == 'internal' and dest_usage != 'internal':
                # Outgoing from internal location
                outward_qty = move.product_qty
                outward_value = abs(valuation)
            elif src_usage == 'internal' and dest_usage == 'internal':
                # Internal transfer - create both entries
                outward_qty = move.product_qty
                outward_value = abs(valuation)
            
            # Get voucher details
            vch_type = move._get_voucher_type()
            vch_no = move.picking_id.name if move.picking_id else move.reference
            particulars = move._get_particulars()
            partner_id = move.partner_id.id if move.partner_id else (move.picking_id.partner_id.id if move.picking_id else False)
            
            # Create ledger entry
            self.env['stock.ledger'].create({
                'date': move.date,
                'product_id': move.product_id.id,
                'particulars': particulars,
                'partner_id': partner_id,
                'vch_type': vch_type,
                'vch_no': vch_no,
                'reference': move.reference,
                'inward_qty': inward_qty,
                'inward_value': inward_value,
                'outward_qty': outward_qty,
                'outward_value': outward_value,
                'closing_qty': 0.0,
                'closing_value': 0.0,
                'company_id': move.company_id.id,
                'stock_move_id': move.id,
                'location_id': move.location_id.id,
                'location_dest_id': move.location_dest_id.id,
            })
    
    def _action_done(self, cancel_backorder=False):
        """Override to create ledger entries when move is done"""
        res = super()._action_done(cancel_backorder=cancel_backorder)
        self._create_stock_ledger_entry()
        return res
