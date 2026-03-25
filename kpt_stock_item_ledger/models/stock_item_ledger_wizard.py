from datetime import timedelta

from odoo import api, fields, models, _


def _get_move_value(env, move):
    """Return absolute value for a stock.move.

    Priority:
    1. stock.valuation.layer (automated costing)
    2. purchase_line_id price (PO linked move)
    3. move.price_unit * quantity
    4. linked vendor bill line (bill-first flow)
    """
    qty = move.quantity or 0.0

    svl_value = sum(move.stock_valuation_layer_ids.mapped('value'))
    if svl_value:
        return abs(svl_value)

    if hasattr(move, 'purchase_line_id') and move.purchase_line_id:
        return abs(move.purchase_line_id.price_unit * qty)

    if move.price_unit:
        return abs(move.price_unit * qty)

    picking = move.picking_id
    if picking:
        bill = env['account.move'].sudo().search([
            ('auto_created_receipt_id', '=', picking.id),
            ('move_type', '=', 'in_invoice'),
        ], limit=1)
        if not bill:
            bill = env['account.move'].sudo().search([
                ('receipt_id', '=', picking.id),
                ('move_type', '=', 'in_invoice'),
            ], limit=1)
        if bill:
            bill_line = bill.invoice_line_ids.filtered(
                lambda l: l.product_id == move.product_id and not l.display_type
            )[:1]
            if bill_line:
                return abs(bill_line.price_unit * qty)

    return 0.0


class StockItemLedgerWizard(models.TransientModel):
    _name = 'stock.item.ledger.wizard'
    _description = 'Stock Item Ledger Wizard'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain="[('type', 'in', ['product', 'consu'])]",
    )
    date_from = fields.Date(
        string='Start Date',
        required=True,
    )
    date_to = fields.Date(
        string='End Date',
        required=True,
    )
    line_ids = fields.One2many(
        'stock.item.ledger.wizard.line',
        'wizard_id',
        string='Lines',
        readonly=True,
    )
    opening_qty = fields.Float(string='Opening Quantity', readonly=True)
    opening_value = fields.Monetary(
        string='Opening Value',
        currency_field='currency_id',
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        readonly=True,
    )

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            self = self.with_company(self.company_id)

    def action_compute_ledger(self):
        self.ensure_one()
        self._generate_lines()
        action = self.env.ref('kpt_stock_item_ledger.action_stock_item_ledger_lines').read()[0]
        action['domain'] = [('wizard_id', '=', self.id)]
        action['context'] = {
            'search_default_group_by_product': 0,
            'default_wizard_id': self.id,
        }
        return action

    def _get_internal_loc_ids(self):
        """Use sudo() so multi-company/security rules don't filter locations."""
        return self.env['stock.location'].sudo().search([
            ('usage', '=', 'internal'),
            '|', ('company_id', '=', self.company_id.id), ('company_id', '=', False),
        ]).ids

    def _move_sign(self, move, internal_loc_ids):
        """Return +1 for in, -1 for out, 0 for internal-to-internal (skip).

        Pure internal transfers previously returned 1 unconditionally which
        inflated the running balance. Return 0 so callers can skip them.
        """
        dest_internal = move.location_dest_id.id in internal_loc_ids
        src_internal = move.location_id.id in internal_loc_ids
        if dest_internal and not src_internal:
            return 1
        if src_internal and not dest_internal:
            return -1
        # Pure internal→internal: return 0 so the caller can skip
        return 0

    def _generate_lines(self):
        self.ensure_one()
        Line = self.env['stock.item.ledger.wizard.line']
        Line.search([('wizard_id', '=', self.id)]).unlink()

        internal_loc_ids = self._get_internal_loc_ids()

        # company_id removed: internal_loc_ids are already company-scoped.
        # Using sudo() so stock ORM rules don't filter out valid moves.
        base_domain = [
            ('product_id', '=', self.product_id.id),
            ('state', '=', 'done'),
            '|',
            ('location_id', 'in', internal_loc_ids),
            ('location_dest_id', 'in', internal_loc_ids),
        ]

        StockMove = self.env['stock.move'].sudo()

        # Opening balance: all done moves before date_from
        opening_domain = base_domain[:]
        if self.date_from:
            opening_domain.append(('date', '<', fields.Datetime.to_datetime(self.date_from)))
        opening_moves = StockMove.search(opening_domain)

        opening_qty = opening_value = 0.0
        for move in opening_moves:
            sign = self._move_sign(move, internal_loc_ids)
            opening_qty += (move.quantity or 0.0) * sign
            opening_value += _get_move_value(self.env, move) * sign

        self.opening_qty = opening_qty
        self.opening_value = opening_value
        balance_qty = opening_qty
        balance_value = opening_value

        # Period movements
        period_domain = base_domain[:]
        if self.date_from:
            period_domain.append(('date', '>=', fields.Datetime.to_datetime(self.date_from)))
        if self.date_to:
            period_domain.append(('date', '<', fields.Datetime.to_datetime(self.date_to) + timedelta(days=1)))

        period_moves = StockMove.search(period_domain, order='date, id')

        for move in period_moves:
            picking = move.picking_id
            sign = self._move_sign(move, internal_loc_ids)
            qty = (move.quantity or 0.0) * sign
            value = _get_move_value(self.env, move) * sign

            in_qty = qty if qty > 0 else 0.0
            in_value = value if value > 0 else 0.0
            out_qty = -qty if qty < 0 else 0.0
            out_value = -value if value < 0 else 0.0

            balance_qty += qty
            balance_value += value

            partner = (picking and picking.partner_id) or move.partner_id

            self.env['stock.item.ledger.wizard.line'].create({
                'wizard_id': self.id,
                'date': move.date.date() if move.date else False,
                'product_id': self.product_id.id,
                'partner_id': partner.id if partner else False,
                'move_id': move.id,
                'reference': (picking and picking.name) or move.reference or move.origin or '',
                'move_type': picking.picking_type_id.name if picking and picking.picking_type_id else '',
                'in_qty': in_qty,
                'in_value': in_value,
                'out_qty': out_qty,
                'out_value': out_value,
                'balance_qty': balance_qty,
                'balance_value': balance_value,
            })


class StockItemLedgerWizardLine(models.TransientModel):
    _name = 'stock.item.ledger.wizard.line'
    _description = 'Stock Item Ledger Line'
    _order = 'date, id'

    wizard_id = fields.Many2one(
        'stock.item.ledger.wizard',
        string='Wizard',
        ondelete='cascade',
    )
    date = fields.Date(string='Date', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    move_id = fields.Many2one('stock.move', string='Stock Move')
    reference = fields.Char(string='Document')
    move_type = fields.Char(string='Type')
    in_qty = fields.Float(string='In Qty')
    in_value = fields.Monetary(string='In Value', currency_field='currency_id')
    out_qty = fields.Float(string='Out Qty')
    out_value = fields.Monetary(string='Out Value', currency_field='currency_id')
    balance_qty = fields.Float(string='Balance Qty')
    balance_value = fields.Monetary(string='Balance Value', currency_field='currency_id')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='wizard_id.company_id',
        store=False,
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='wizard_id.currency_id',
        store=False,
        readonly=True,
    )

