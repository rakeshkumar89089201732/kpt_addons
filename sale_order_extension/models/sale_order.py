
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError
from odoo.tools.misc import formatLang

class SaleOrder(models.Model):
    """This is used to inherit 'sale.order' to add new fields and
    functionality"""
    _inherit = 'sale.order'



    def _get_default_cash_rounding(self, company=None):
        company = company or self.env.company
        CashRounding = self.env['account.cash.rounding']
        rounding = CashRounding.search([
            ('company_id', '=', company.id),
            ('name', 'ilike', 'round off'),
        ], limit=1)
        if not rounding:
            rounding = CashRounding.search([
                ('company_id', '=', company.id),
            ], limit=1)
        return rounding

    invoice_cash_rounding_id = fields.Many2one(
        comodel_name='account.cash.rounding',
        string='Cash Rounding',
        default=lambda self: self._get_default_cash_rounding(),
        readonly=False,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help='Defines the smallest coinage of the currency that can be used to pay by cash.'
    )

    partner_invoice_id = fields.Many2one(
        comodel_name='res.partner',
        string="Invoice Address",
        compute='_compute_partner_invoice_id',
        domain="[('type', '=', 'invoice')]",
        store=True, readonly=False, required=True, precompute=True,
        check_company=True,
        index='btree_not_null',
    )

    partner_shipping_id = fields.Many2one(
        comodel_name='res.partner',
        string="Delivery Address",
        domain="[('type', '=', 'delivery')]",
        compute='_compute_partner_shipping_id',
        store=True, readonly=False, required=True, precompute=True,
        check_company=True,
        index='btree_not_null')

    sale_order_reference = fields.Char(string='Order Reference')
    round_off_amount = fields.Monetary(
        string='Round Off Amount',
        compute='_compute_kpt_rounding_compat',
        inverse='_inverse_round_off_amount',
        currency_field='currency_id',
        store=True,
        readonly=False,
    )
    amount_total_rounded = fields.Monetary(
        string='Rounded Total',
        compute='_compute_kpt_rounding_compat',
        currency_field='currency_id',
        store=True,
    )
    amount_total_difference = fields.Monetary(
        string='Round Off Difference',
        compute='_compute_kpt_rounding_compat',
        currency_field='currency_id',
        store=True,
    )
    round_off_manual = fields.Boolean(copy=False, default=False)
    round_off_manual_amount = fields.Monetary(currency_field='currency_id', copy=False)

    is_send_products = fields.Boolean(compute='_compute_is_send_products')


    def _compute_is_send_products(self):
        for sale in self:
            if sale.order_line and sale.picking_ids and sale.order_line.filtered(lambda x: x.product_uom_qty != x.qty_delivered):
                sale.is_send_products = True
            else:
                sale.is_send_products = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('invoice_cash_rounding_id'):
                company = self.env['res.company'].browse(vals.get('company_id')) if vals.get('company_id') else self.env.company
                rounding = self._get_default_cash_rounding(company=company)
                if rounding:
                    vals['invoice_cash_rounding_id'] = rounding.id
        return super().create(vals_list)


    def _prepare_invoice(self):
        """Override to pass cash rounding to invoice."""
        invoice_vals = super()._prepare_invoice()
        if self.invoice_cash_rounding_id:
            invoice_vals['invoice_cash_rounding_id'] = self.invoice_cash_rounding_id.id
        return invoice_vals

    def _get_cash_rounding_difference(self):
        self.ensure_one()
        if not self.invoice_cash_rounding_id:
            return 0.0
        return self.invoice_cash_rounding_id.compute_difference(self.currency_id, self.amount_total or 0.0)

    @api.depends(
        'amount_total',
        'invoice_cash_rounding_id',
        'invoice_cash_rounding_id.rounding',
        'invoice_cash_rounding_id.rounding_method',
        'round_off_manual',
        'round_off_manual_amount',
    )
    def _compute_kpt_rounding_compat(self):
        for order in self:
            computed_round_off = order._get_cash_rounding_difference()
            order.round_off_amount = order.round_off_manual_amount if order.round_off_manual else computed_round_off
            order.amount_total_difference = order.round_off_amount
            order.amount_total_rounded = (order.amount_total or 0.0) + order.round_off_amount

    def _inverse_round_off_amount(self):
        for order in self:
            computed_round_off = order._get_cash_rounding_difference()
            if order.invoice_cash_rounding_id and not order.currency_id.is_zero(order.round_off_amount - computed_round_off):
                order.round_off_manual = True
                order.round_off_manual_amount = order.round_off_amount
            else:
                order.round_off_manual = False
                order.round_off_manual_amount = 0.0

    @api.onchange('invoice_cash_rounding_id')
    def _onchange_invoice_cash_rounding_id(self):
        for order in self:
            order.round_off_manual = False
            order.round_off_manual_amount = 0.0

    @api.onchange('company_id')
    def _onchange_company_id_set_cash_rounding(self):
        for order in self:
            if not order.invoice_cash_rounding_id:
                order.invoice_cash_rounding_id = order._get_default_cash_rounding(company=order.company_id)

    @api.depends_context('lang')
    @api.depends(
        'order_line.tax_id',
        'order_line.price_unit',
        'amount_total',
        'amount_untaxed',
        'currency_id',
        'invoice_cash_rounding_id',
        'invoice_cash_rounding_id.rounding',
        'invoice_cash_rounding_id.rounding_method',
        'round_off_amount',
    )
    def _compute_tax_totals(self):
        for order in self:
            order = order.with_company(order.company_id)
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            totals = order.env['account.tax']._prepare_tax_totals(
                [x._convert_to_tax_base_line_dict() for x in order_lines],
                order.currency_id or order.company_id.currency_id,
            )
            totals['display_rounding'] = bool(order.invoice_cash_rounding_id)
            totals['rounding_amount'] = order.round_off_amount if order.invoice_cash_rounding_id else 0.0
            totals['formatted_rounding_amount'] = formatLang(
                self.env,
                totals['rounding_amount'],
                currency_obj=order.currency_id,
            )
            totals['amount_total'] = (totals.get('amount_total') or 0.0) + totals['rounding_amount']
            totals['formatted_amount_total'] = formatLang(
                self.env,
                totals['amount_total'],
                currency_obj=order.currency_id,
            )
            order.tax_totals = totals


    def _find_mail_template(self):
        """ Get the appropriate mail template for the current sales order based on its state.

        If the SO is confirmed, we return the mail template for the sale confirmation.
        Otherwise, we return the quotation email template.

        :return: The correct mail template based on the current status
        :rtype: record of `mail.template` or `None` if not found
        """
        self.ensure_one()
        if self.env.context.get('proforma') or self.state != 'sale':
            if self.env.context.get('proforma'):
                return self.env.ref('sale_order_extension.email_template_edi_sale', raise_if_not_found=False)
            return self.env.ref('sale_order_extension.email_template_edi_sale_quotation',
                                raise_if_not_found=False)
        else:
            return self._get_confirmation_template()


    def action_revert(self):
        self.ensure_one()
        self.state = 'draft'

    def action_quotation_send(self):
        """ Opens a wizard to compose an email, with relevant mail template loaded by default """
        self.ensure_one()
        if not self.order_line:
            raise ValidationError(_("Please add product before send quotation / proforma"))

        for line in self.order_line:
            if not line.price_unit and not line.display_type:
                raise ValidationError(_(f"{line.product_template_id.display_name or line.name} product unit price cannot be 0.00"))
        self.order_line._validate_analytic_distribution()
        lang = self.env.context.get('lang')
        mail_template = self._find_mail_template()
        if mail_template and mail_template.lang:
            lang = mail_template._render_lang(self.ids)[self.id]
        ctx = {
            'default_model': 'sale.order',
            'default_res_ids': self.ids,
            'default_template_id': mail_template.id if mail_template else None,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
            'proforma': self.env.context.get('proforma', False),
            'force_email': True,
            'model_description': self.with_context(lang=lang).type_name,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    def unlink(self):
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_("You do not have access to delete Sale Orders. Only Administrators can delete them."))
        return super(SaleOrder, self).unlink()

    def action_send_products(self):
        return self.action_view_delivery()



