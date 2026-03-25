from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockLedgerWizard(models.TransientModel):
    _name = 'stock.ledger.wizard'
    _description = 'Stock Ledger Report Wizard'

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
    )
    date_from = fields.Date(
        string='From Date',
        required=True,
        default=fields.Date.context_today,
    )
    date_to = fields.Date(
        string='To Date',
        required=True,
        default=fields.Date.context_today,
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        domain=[('usage', '=', 'internal')],
        help='Leave empty to include all internal locations',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )
    show_zero_lines = fields.Boolean(
        string='Show Zero Quantity Lines',
        default=False,
    )

    def action_generate_ledger(self):
        """Generate stock ledger report"""
        self.ensure_one()
        
        if self.date_from > self.date_to:
            raise UserError(_('From Date cannot be greater than To Date'))
        
        # Delete existing ledger entries for this product in the date range
        domain = [
            ('product_id', '=', self.product_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
        ]
        
        if self.location_id:
            domain.extend([
                '|',
                ('location_id', '=', self.location_id.id),
                ('location_dest_id', '=', self.location_id.id),
            ])
        
        # Clear old ledger entries
        self.env['stock.ledger'].search(domain).unlink()
        
        # Calculate opening balance
        opening_qty, opening_value = self._get_opening_balance()
        
        # Create opening balance entry
        if opening_qty != 0 or opening_value != 0:
            self.env['stock.ledger'].create({
                'date': self.date_from,
                'product_id': self.product_id.id,
                'particulars': 'Opening Balance',
                'vch_type': 'opening',
                'vch_no': '',
                'inward_qty': 0.0,
                'inward_value': 0.0,
                'outward_qty': 0.0,
                'outward_value': 0.0,
                'closing_qty': opening_qty,
                'closing_value': opening_value,
                'company_id': self.company_id.id,
            })
        
        # Get all stock moves in the date range
        move_domain = [
            ('product_id', '=', self.product_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', '=', 'done'),
            ('company_id', '=', self.company_id.id),
        ]
        
        if self.location_id:
            move_domain.extend([
                '|',
                ('location_id', '=', self.location_id.id),
                ('location_dest_id', '=', self.location_id.id),
            ])
        
        stock_moves = self.env['stock.move'].search(move_domain, order='date, id')
        
        # Create ledger entries from stock moves
        for move in stock_moves:
            move._create_stock_ledger_entry()
        
        # Calculate running balance
        self._calculate_closing_balance()
        
        # Open the ledger view
        return {
            'name': _('Stock Ledger - %s') % self.product_id.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.ledger',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {
                'search_default_product_id': self.product_id.id,
                'default_product_id': self.product_id.id,
            },
        }
    
    def _get_opening_balance(self):
        """Calculate opening balance for the product"""
        opening_qty = 0.0
        opening_value = 0.0
        
        # Get all moves before the from_date
        move_domain = [
            ('product_id', '=', self.product_id.id),
            ('date', '<', self.date_from),
            ('state', '=', 'done'),
            ('company_id', '=', self.company_id.id),
        ]
        
        if self.location_id:
            move_domain.extend([
                '|',
                ('location_id', '=', self.location_id.id),
                ('location_dest_id', '=', self.location_id.id),
            ])
        
        stock_moves = self.env['stock.move'].search(move_domain)
        
        for move in stock_moves:
            src_usage = move.location_id.usage
            dest_usage = move.location_dest_id.usage
            
            # Get valuation
            valuation = 0.0
            if move.stock_valuation_layer_ids:
                valuation = sum(move.stock_valuation_layer_ids.mapped('value'))
            else:
                valuation = move.product_qty * move.product_id.standard_price
            
            # Calculate based on location
            if dest_usage == 'internal' and src_usage != 'internal':
                # Incoming
                opening_qty += move.product_qty
                opening_value += abs(valuation)
            elif src_usage == 'internal' and dest_usage != 'internal':
                # Outgoing
                opening_qty -= move.product_qty
                opening_value -= abs(valuation)
        
        return opening_qty, opening_value
    
    def _calculate_closing_balance(self):
        """Calculate running closing balance for all ledger entries"""
        domain = [
            ('product_id', '=', self.product_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
        ]
        
        if self.location_id:
            domain.extend([
                '|',
                ('location_id', '=', self.location_id.id),
                ('location_dest_id', '=', self.location_id.id),
            ])
        
        ledger_entries = self.env['stock.ledger'].search(domain, order='date, id')
        
        running_qty = 0.0
        running_value = 0.0
        
        for entry in ledger_entries:
            if entry.vch_type == 'opening':
                # Opening balance sets the initial values
                running_qty = entry.closing_qty
                running_value = entry.closing_value
            else:
                # Add inward, subtract outward
                running_qty += entry.inward_qty - entry.outward_qty
                running_value += entry.inward_value - entry.outward_value
                
                # Update closing balance
                entry.write({
                    'closing_qty': running_qty,
                    'closing_value': running_value,
                })
