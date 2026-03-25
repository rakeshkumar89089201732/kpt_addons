from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    receipt_id = fields.Many2one(
        'stock.picking',
        string='Related Receipt',
        copy=False,
        domain=[('picking_type_code', '=', 'incoming')]
    )
    auto_created_receipt_id = fields.Many2one(
        'stock.picking',
        string='Auto Created Receipt',
        copy=False,
        readonly=True
    )
    has_receipt = fields.Boolean(
        string='Has Receipt',
        compute='_compute_has_receipt',
        store=True
    )
    auto_created_purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Auto Created Purchase Order',
        copy=False,
        readonly=True
    )

    @api.depends('receipt_id', 'auto_created_receipt_id')
    def _compute_has_receipt(self):
        for move in self:
            move.has_receipt = bool(move.receipt_id or move.auto_created_receipt_id)

    def action_apply_tds(self):
        """Open wizard to apply TDS taxes to vendor bill"""
        self.ensure_one()
        return {
            'name': _('Apply TDS Taxes'),
            'type': 'ir.actions.act_window',
            'res_model': 'apply.tds.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_id': self.id,
            }
        }

    def action_post(self):
        # Apply company default purchase rounding before posting so the extra line is included
        self._apply_purchase_rounding()

        res = super(AccountMove, self).action_post()
        
        for move in self:
            if move.move_type != 'in_invoice':
                continue

            if not move.partner_id or not move.invoice_line_ids:
                continue

            po = False
            if not move.auto_created_purchase_order_id:
                po = move._create_purchase_order_from_bill()
                if po:
                    move.auto_created_purchase_order_id = po.id

            if not move.receipt_id and not move.auto_created_receipt_id:
                receipt = move._create_receipt_from_bill(purchase_order=po or move.auto_created_purchase_order_id)
                if receipt:
                    move.auto_created_receipt_id = receipt.id
        
        return res

    def _apply_purchase_rounding(self):
        """Set cash rounding on vendor bills using company default and recompute lines."""
        for move in self:
            if move.move_type != 'in_invoice':
                continue

            rounding = move.company_id.purchase_cash_rounding_id
            if not rounding:
                continue

            # Only apply if not already set; let manual choices win
            if not move.cash_rounding_id:
                move.cash_rounding_id = rounding
                move._recompute_cash_rounding_lines()

    def _create_purchase_order_from_bill(self):
        self.ensure_one()

        lines = self.invoice_line_ids.filtered(lambda l: not l.display_type and l.product_id and l.quantity)
        if not self.partner_id or not lines:
            return False

        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('warehouse_id.company_id', '=', self.company_id.id)
        ], limit=1)

        order_vals = {
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'date_order': fields.Datetime.now(),
            'origin': self.name,
        }
        if picking_type and 'picking_type_id' in self.env['purchase.order']._fields:
            order_vals['picking_type_id'] = picking_type.id

        order_lines = []
        for line in lines:
            order_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.name or line.product_id.display_name,
                'product_qty': line.quantity,
                'product_uom': line.product_uom_id.id,
                'price_unit': line.price_unit,
                'taxes_id': [(6, 0, line.tax_ids.ids)],
                'date_planned': fields.Datetime.now(),
            }))

        order_vals['order_line'] = order_lines
        return self.env['purchase.order'].create(order_vals)

    def _create_receipt_from_bill(self, purchase_order=None):
        self.ensure_one()
        
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('warehouse_id.company_id', '=', self.company_id.id)
        ], limit=1)
        
        if not picking_type:
            return False
        
        location_dest = picking_type.default_location_dest_id
        if not location_dest:
            location_dest = self.env['stock.location'].search([
                ('usage', '=', 'internal'),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
        
        location_src = self.partner_id.property_stock_supplier
        if not location_src:
            location_src = self.env.ref('stock.stock_location_suppliers', raise_if_not_found=False)
        
        if not location_src or not location_dest:
            return False
        
        picking_vals = {
            'partner_id': self.partner_id.id,
            'picking_type_id': picking_type.id,
            'location_id': location_src.id,
            'location_dest_id': location_dest.id,
            'origin': purchase_order.name if purchase_order else self.name,
            'company_id': self.company_id.id,
            'move_type': 'direct',
        }
        if purchase_order and 'purchase_id' in self.env['stock.picking']._fields:
            picking_vals['purchase_id'] = purchase_order.id
        
        picking = self.env['stock.picking'].with_context(default_move_type='direct').create(picking_vals)
        
        for line in self.invoice_line_ids.filtered(lambda l: l.product_id and l.product_id.type in ['product', 'consu']):
            unit_price = line.currency_id._convert(
                line.price_unit,
                self.company_id.currency_id,
                self.company_id,
                self.invoice_date or fields.Date.context_today(self),
            )
            move_vals = {
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.product_uom_id.id,
                'picking_id': picking.id,
                'location_id': location_src.id,
                'location_dest_id': location_dest.id,
                'company_id': self.company_id.id,
            }
            if 'price_unit' in self.env['stock.move']._fields:
                move_vals['price_unit'] = unit_price
            if purchase_order and 'purchase_line_id' in self.env['stock.move']._fields:
                po_line = purchase_order.order_line.filtered(lambda pol: pol.product_id == line.product_id)[:1]
                if po_line:
                    move_vals['purchase_line_id'] = po_line.id
            self.env['stock.move'].create(move_vals)
        
        # Bill-first flow: receive products immediately (validate receipt)
        if picking.move_ids_without_package:
            picking.action_confirm()
            picking.action_assign()
            for move in picking.move_ids_without_package:
                move.quantity = move.product_uom_qty
            picking.button_validate()
        
        return picking

    def action_view_receipt(self):
        self.ensure_one()
        receipt = self.receipt_id or self.auto_created_receipt_id
        
        if not receipt:
            raise UserError(_('No receipt found for this bill.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Receipt'),
            'res_model': 'stock.picking',
            'res_id': receipt.id,
            'view_mode': 'form',
            'view_id': self.env.ref('stock.view_picking_form').id,
            'target': 'current',
        }
