from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    vendor_bill_ids = fields.One2many(
        'account.move', 
        'receipt_id', 
        string='Vendor Bills',
        domain=[('move_type', '=', 'in_invoice')]
    )
    auto_created_vendor_bill_ids = fields.One2many(
        'account.move',
        'auto_created_receipt_id',
        string='Auto Created Vendor Bills',
        domain=[('move_type', '=', 'in_invoice')]
    )
    vendor_bill_count = fields.Integer(
        string='Bill Count',
        compute='_compute_vendor_bill_count'
    )

    @api.depends('vendor_bill_ids', 'auto_created_vendor_bill_ids')
    def _compute_vendor_bill_count(self):
        for picking in self:
            picking.vendor_bill_count = len(picking.vendor_bill_ids) + len(picking.auto_created_vendor_bill_ids)

    def action_create_vendor_bill(self):
        self.ensure_one()
        
        if self.picking_type_code != 'incoming':
            raise UserError(_('You can only create vendor bills from incoming receipts.'))
        
        if self.state != 'done':
            raise UserError(_('You can only create vendor bills from validated receipts.'))
        
        if not self.partner_id:
            raise UserError(_('Please set a vendor on the receipt first.'))

        bill_vals = self._prepare_vendor_bill_values()
        bill = self.env['account.move'].create(bill_vals)
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Vendor Bill'),
            'res_model': 'account.move',
            'res_id': bill.id,
            'view_mode': 'form',
            'view_id': self.env.ref('account.view_move_form').id,
            'target': 'current',
        }

    def _prepare_vendor_bill_values(self):
        self.ensure_one()
        
        invoice_lines = []
        for move in self.move_ids_without_package.filtered(lambda m: m.state == 'done' and m.product_id):
            line_vals = {
                'product_id': move.product_id.id,
                'name': move.product_id.display_name,
                'quantity': move.quantity,
                'product_uom_id': move.product_uom.id,
                'price_unit': move.product_id.standard_price or 0.0,
            }
            invoice_lines.append((0, 0, line_vals))
        
        return {
            'move_type': 'in_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.context_today(self),
            'receipt_id': self.id,
            'invoice_origin': self.name,
            'invoice_line_ids': invoice_lines,
        }

    def action_view_vendor_bills(self):
        self.ensure_one()
        action = self.env.ref('account.action_move_in_invoice_type').read()[0]
        bills = self.vendor_bill_ids | self.auto_created_vendor_bill_ids
        
        if len(bills) == 1:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = bills[0].id
        else:
            action['domain'] = [('id', 'in', bills.ids)]
        
        action['context'] = {
            'default_move_type': 'in_invoice',
            'default_receipt_id': self.id,
        }
        return action
