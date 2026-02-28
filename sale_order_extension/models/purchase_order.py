from odoo import models, fields, api, _
from odoo.tools import float_compare

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    purchase_order_reference = fields.Char(string='Order Reference')

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

    @api.depends('amount_total')
    def _compute_price_total_rounded(self):
        """Compute the rounded value of the price_total field."""
        for purchase in self:
            purchase.amount_total_rounded = round(purchase.amount_total) if purchase.amount_total else 0.0

    @api.depends('amount_total', 'amount_total_rounded')
    def _compute_price_total_difference(self):
        """Compute the difference between the rounded value and the original price_total."""
        for purchase in self:
            purchase.amount_total_difference = (purchase.amount_total_rounded - purchase.amount_total) if purchase.amount_total else 0.0



    def action_rfq_send(self):
        '''
        This function opens a window to compose an email, with the edi purchase template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data._xmlid_lookup('sale_order_extension.email_template_kpt_purchase')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data._xmlid_lookup('mail.email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'purchase.order',
            'default_res_ids': self.ids,
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'default_email_layout_xmlid': "mail.mail_notification_layout_with_responsible_signature",
            'force_email': True,
            'mark_rfq_as_sent': True,
        })

        # In the case of a RFQ or a PO, we want the "View..." button in line with the state of the
        # object. Therefore, we pass the model description in the context, in the language in which
        # the template is rendered.
        lang = self.env.context.get('lang')
        if {'default_template_id', 'default_model', 'default_res_id'} <= ctx.keys():
            template = self.env['mail.template'].browse(ctx['default_template_id'])
            if template and template.lang:
                lang = template._render_lang([ctx['default_res_id']])[ctx['default_res_id']]

        self = self.with_context(lang=lang)
        if self.state in ['draft', 'sent']:
            ctx['model_description'] = _('Request for Quotation')
        else:
            ctx['model_description'] = _('Purchase Order')

        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def print_quotation(self):
        self.write({'state': "sent"})
        return self.env.ref('sale_order_extension.action_report_kpt_purchase').report_action(self)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.depends('product_packaging_id', 'product_uom', 'product_qty')
    def _compute_product_packaging_qty(self):
        for line in self:
            if not line.product_packaging_id:
                continue

    @api.depends('product_packaging_qty')
    def _compute_product_qty(self):
        for line in self:
            if line.product_packaging_id:
                pass



