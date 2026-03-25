from datetime import timedelta

from odoo import api, fields, models, _
from odoo.tools.misc import format_date


class StockItemLedgerReportHandler(models.AbstractModel):
    _name = 'kpt.stock.item.ledger.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Stock Item Ledger Report Handler'

    # -----------------------------------------------------------------------
    # Options
    # -----------------------------------------------------------------------

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        # Fix: use setdefault so manual user collapse/expand of lines is respected
        # Previously `options['unfold_all'] = True` was unconditional and ignored previous_options
        options.setdefault('unfold_all', True)
        options.setdefault('buttons', [])

        prev = previous_options or {}
        options['kpt_product_id'] = prev.get('kpt_product_id', False)
        options['kpt_product_name'] = prev.get('kpt_product_name', '')

        # Fix: explicitly carry forward the search bar text from previous_options.
        # Odoo 17 core (_init_options_search_bar) only copies filter_search_bar when previous_options
        # is not None AND 'default_filter_accounts' is absent from context. The custom handler
        # must mirror this key here so _get_product() can read it on every render cycle.
        # Without this, the first/subsequent renders after a search lose the typed product text.
        if 'filter_search_bar' in prev:
            options['filter_search_bar'] = prev['filter_search_bar']

        # Removed: dead kpt_product_filter dict that was set here but never consumed anywhere.
        # The product is resolved solely via options['kpt_product_id'] or options['filter_search_bar']
        # inside _get_product().

    # -----------------------------------------------------------------------
    # Product helpers
    # -----------------------------------------------------------------------

    def _get_filter_product(self, options):
        """Get product filter options for the UI."""
        return {
            'id': 'product_id',
            'name': _('Product'),
            'filter': 'product_id',
            'component': 'product_autocomplete',
        }

    def _set_filter_product(self, options, product_id):
        """Set the selected product in options."""
        if product_id:
            product = self.env['product.product'].browse(product_id).exists()
            if product:
                options['kpt_product_id'] = product.id
                options['kpt_product_name'] = product.display_name
        else:
            options['kpt_product_id'] = False
            options['kpt_product_name'] = ''

    def _get_product(self, options):
        """Return selected product.product or False."""
        # First check if product_id is explicitly set
        pid = options.get('kpt_product_id')
        if pid:
            return self.env['product.product'].browse(pid).exists()
        
        # Check search bar for product name/code
        search = (options.get('filter_search_bar') or '').strip()
        if search:
            # Try partial match on default_code first
            product = self.env['product.product'].search([
                ('default_code', 'ilike', f"%{search}%"),
                ('type', 'in', ['product', 'consu'])
            ], limit=1)
            
            if not product:
                # Try partial name match
                product = self.env['product.product'].search([
                    ('name', 'ilike', f"%{search}%"),
                    ('type', 'in', ['product', 'consu'])
                ], limit=1)
            
            if product:
                # Cache it in options
                options['kpt_product_id'] = product.id
                options['kpt_product_name'] = product.display_name
                return product
        
        return False

    # -----------------------------------------------------------------------
    # Data computation (uses stock.move – works for ALL products)
    # -----------------------------------------------------------------------

    def _get_internal_loc_ids(self, company):
        """
        Return IDs of all internal stock locations for the given company.
        Uses sudo() because this method is called from the account.report
        framework which may not have stock.location access rights.
        """
        return self.env['stock.location'].sudo().search([
            ('usage', '=', 'internal'),
            '|', ('company_id', '=', company.id), ('company_id', '=', False),
        ]).ids

    def _move_sign(self, move, internal_loc_ids):
        """Return +1 if move brings stock IN, -1 if it takes stock OUT, 0 to skip.

        Internal→internal transfers show up in BOTH _compute_ledger sides
        and should not double-count. We report them as +1 (dest) so the
        balance increases at the destination warehouse, but returning 0 for
        true internal transfers keeps the running balance consistent.
        """
        dest_is_internal = move.location_dest_id.id in internal_loc_ids
        src_is_internal = move.location_id.id in internal_loc_ids
        if dest_is_internal and not src_is_internal:
            return 1   # incoming from vendor/customer
        if src_is_internal and not dest_is_internal:
            return -1  # outgoing to vendor/customer
        # Pure internal→internal: skip to avoid double-counting
        # Previously returned 1 unconditionally which inflated the balance.
        return 0

    def _move_value(self, move):
        """Return absolute value of a stock move (always positive).

        Priority:
        1. stock.valuation.layer (automated costing products)
        2. purchase.order.line price (if linked via purchase_line_id)
        3. move.price_unit * quantity
        4. linked vendor bill line price_unit * quantity
        """
        qty = move.quantity or move.product_uom_qty or 0.0

        # 1. Valuation layers
        svl_value = sum(move.stock_valuation_layer_ids.mapped('value'))
        if svl_value:
            return abs(svl_value)

        # 2. PO line price
        if hasattr(move, 'purchase_line_id') and move.purchase_line_id:
            return abs(move.purchase_line_id.price_unit * qty)

        # 3. move.price_unit
        if move.price_unit:
            return abs(move.price_unit * qty)

        # 4. Find linked vendor bill line via auto_created_receipt_id
        picking = move.picking_id
        if picking:
            # check if a bill was auto-created for this picking
            bill_move = self.env['account.move'].sudo().search([
                ('auto_created_receipt_id', '=', picking.id),
                ('move_type', '=', 'in_invoice'),
            ], limit=1)
            if not bill_move:
                bill_move = self.env['account.move'].sudo().search([
                    ('receipt_id', '=', picking.id),
                    ('move_type', '=', 'in_invoice'),
                ], limit=1)
            if bill_move:
                bill_line = bill_move.invoice_line_ids.filtered(
                    lambda l: l.product_id == move.product_id and not l.display_type
                )[:1]
                if bill_line:
                    return abs(bill_line.price_unit * qty)

        return 0.0

    def _compute_ledger(self, company, product, date_from, date_to):
        """
        Returns (opening_qty, opening_value, [movement_dict, ...]).
        Uses stock.move(state=done) so it works regardless of costing method.

        IMPORTANT: All stock.move / stock.location searches use sudo() because
        the account.report framework runs in accounting context and the ORM
        security rules for stock models may restrict results. sudo() ensures
        we see all moves for the company, matching the Inventory module's
        own behaviour in its built-in reports.
        """
        internal_loc_ids = self._get_internal_loc_ids(company)

        # Base domain: product + done state + must touch an internal location
        # Note: company_id filter removed — internal_loc_ids are already
        # company-scoped, so any move involving them belongs to this company.
        # Adding company_id caused false negatives when the move's company_id
        # didn't match the expected value (e.g. branches/multi-company edge cases).
        base_domain = [
            ('product_id', '=', product.id),
            ('state', '=', 'done'),
            '|',
            ('location_id', 'in', internal_loc_ids),
            ('location_dest_id', 'in', internal_loc_ids),
        ]

        StockMove = self.env['stock.move'].sudo()

        # Opening balance: all done moves BEFORE date_from
        opening_moves = StockMove.search(
            base_domain + [('date', '<', fields.Datetime.to_datetime(date_from))]
        )
        opening_qty = opening_value = 0.0
        for move in opening_moves:
            sign = self._move_sign(move, internal_loc_ids)
            # Skip internal→internal transfers (sign=0) to avoid double-counting
            if not sign:
                continue
            qty = move.quantity or move.product_uom_qty or 0.0
            opening_qty += qty * sign
            opening_value += self._move_value(move) * sign

        # Period moves
        period_moves = StockMove.search(
            base_domain + [
                ('date', '>=', fields.Datetime.to_datetime(date_from)),
                ('date', '<', fields.Datetime.to_datetime(date_to) + timedelta(days=1)),
            ],
            order='date, id'
        )

        balance_qty = opening_qty
        balance_value = opening_value
        movements = []

        for move in period_moves:
            sign = self._move_sign(move, internal_loc_ids)
            # Skip internal→internal transfers (sign=0) to avoid double-counting
            if not sign:
                continue
            qty_raw = move.quantity or move.product_uom_qty or 0.0
            qty = qty_raw * sign
            value = self._move_value(move) * sign

            in_qty = qty if qty > 0 else 0.0
            in_value = value if value > 0 else 0.0
            out_qty = -qty if qty < 0 else 0.0
            out_value = -value if value < 0 else 0.0

            balance_qty += qty
            balance_value += value

            picking = move.picking_id
            partner = picking.partner_id or move.partner_id
            reference = (picking and picking.name) or move.reference or move.origin or ''

            movements.append({
                # Use None (not False) for missing dates; _format_value returns '' for None
                # but crashes when figure_type='date' and value is False.
                'date': move.date.date() if move.date else None,
                'document': reference,
                'partner_name': partner.display_name if partner else '',
                'in_qty': in_qty,
                'in_value': in_value,
                'out_qty': out_qty,
                'out_value': out_value,
                'balance_qty': balance_qty,
                'balance_value': balance_value,
            })

        return opening_qty, opening_value, movements

    # -----------------------------------------------------------------------
    # Dynamic lines
    # -----------------------------------------------------------------------

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        # Odoo 17 contract: super() should be called to allow base handler participation.
        # The base account.report.custom.handler._dynamic_lines_generator returns an empty list,
        # so calling it is safe. Commented out per project coding standards:
        # super()._dynamic_lines_generator(report, options, all_column_groups_expression_totals, warnings=warnings)
        company = self.env.company
        product = self._get_product(options)

        if not product:
            return [(0, {
                'id': report._get_generic_line_id(None, None, markup='no_product'),
                'name': _('Type a product name or code in the Search box above to view its stock ledger.'),
                'columns': [{} for _c in options['columns']],
                'level': 1,
                'unfoldable': False,
                'unfolded': False,
            })]

        date_from = fields.Date.from_string(options['date']['date_from'])
        date_to = fields.Date.from_string(options['date']['date_to'])

        opening_qty, opening_value, movements = self._compute_ledger(
            company, product, date_from, date_to
        )

        currency = company.currency_id

        def make_cols(vals):
            """
            Build column dicts for a line.
            IMPORTANT: `_format_value` returns '' for None but crashes on
            False when figure_type='date'. Always pass None (not False) for
            empty date cells.
            """
            cols = []
            for col in options['columns']:
                expr = col['expression_label']
                val = vals.get(expr)

                # Normalise: False → None so _format_value handles it as blank
                if val is False:
                    val = None

                curr = currency if expr in ('in_value', 'out_value', 'balance_value') else None
                try:
                    cols.append(report._build_column_dict(val, col, options=options, currency=curr))
                except Exception:
                    # Fallback to empty column rather than crash
                    cols.append({})
            return cols

        lines = []

        # ---- Product header ----
        product_name = f"{product.display_name} [{product.default_code}]" if product.default_code else product.display_name
        lines.append({
            'id': report._get_generic_line_id('product.product', product.id),
            'name': product_name,
            'columns': [{} for _c in options['columns']],
            'level': 0,
            'unfoldable': False,
            'unfolded': True,
            'class': 'o_account_reports_level0',
        })

        # ---- Opening balance ----
        lines.append({
            'id': report._get_generic_line_id('product.product', product.id, markup='opening'),
            'name': _('Opening Balance'),
            'columns': make_cols({
                # None so _format_value returns '' instead of crashing on False
                'date': None, 'document': '', 'partner_name': '',
                'in_qty': None, 'in_value': None,
                'out_qty': None, 'out_value': None,
                'balance_qty': opening_qty, 'balance_value': opening_value,
            }),
            'level': 1,
            'unfoldable': False,
            'unfolded': True,
            'class': 'o_account_reports_initial_balance',
        })

        # ---- Movement rows ----
        for idx, mv in enumerate(movements, start=1):
            lines.append({
                'id': report._get_generic_line_id('product.product', product.id, markup=f'mv_{idx}'),
                'name': '',
                'columns': make_cols(mv),
                'level': 1,
                'unfoldable': False,
                'unfolded': True,
            })

        # ---- Closing balance ----
        close_qty = opening_qty + sum(
            (mv['in_qty'] - mv['out_qty']) for mv in movements
        )
        close_value = opening_value + sum(
            (mv['in_value'] - mv['out_value']) for mv in movements
        )
        lines.append({
            'id': report._get_generic_line_id('product.product', product.id, markup='closing'),
            'name': _('Closing Balance'),
            'columns': make_cols({
                # None so _format_value returns '' instead of crashing on False
                'date': None, 'document': '', 'partner_name': '',
                'in_qty': None, 'in_value': None,
                'out_qty': None, 'out_value': None,
                'balance_qty': close_qty, 'balance_value': close_value,
            }),
            'level': 0,
            'unfoldable': False,
            'unfolded': True,
            'class': 'o_account_reports_level0 total',
        })

        return [(0, line) for line in lines]
