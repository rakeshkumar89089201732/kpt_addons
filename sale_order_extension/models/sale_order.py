
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError
from odoo.fields import Command

class SaleOrder(models.Model):
    """This is used to inherit 'sale.order' to add new fields and
    functionality"""
    _inherit = 'sale.order'



    amount_total_rounded = fields.Float(
        string="Rounded Total",
        compute="_compute_price_total_rounded",
        store=True,
        help="Price Total rounded to the nearest integer."
    )

    amount_total_difference = fields.Float(
        string="Rounding Difference",
        compute="_compute_price_total_difference",
        store=True,
        help="Difference between the rounded price total and the original price total."
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

    is_send_products = fields.Boolean(compute='_compute_is_send_products')


    def _compute_is_send_products(self):
        for sale in self:
            if sale.order_line and sale.picking_ids and sale.order_line.filtered(lambda x: x.product_uom_qty != x.qty_delivered):
                sale.is_send_products = True
            else:
                sale.is_send_products = False


    @api.depends('amount_total')
    def _compute_price_total_rounded(self):
        """Compute the rounded value of the price_total field."""
        for sale in self:
            sale.amount_total_rounded = round(sale.amount_total) if sale.amount_total else 0.0

    @api.depends('amount_total', 'amount_total_rounded')
    def _compute_price_total_difference(self):
        """Compute the difference between the rounded value and the original price_total."""
        for sale in self:
            sale.amount_total_difference = (sale.amount_total_rounded - sale.amount_total) if sale.amount_total else 0.0


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



