# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Gayathri V(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

from odoo import models, fields, _, api
from odoo.exceptions import UserError
from odoo.tools.populate import compute
from odoo.tools import pdf

class SaleOrder(models.Model):
    """This is used to inherit 'sale.order' to add new fields and
    functionality"""
    _inherit = 'sale.order'

    state = fields.Selection(
        selection_add=[('waiting_for_approval', 'Waiting For Approval'),('sent',),
                       ('sale',)])
    approval_user_id = fields.Many2one('res.users',
                                       string='Discount Approved By',
                                       help='The discount approver')

    reject_reason_ids = fields.One2many('discount.reject.reason', 'sale_order_id')
    is_discount_approval = fields.Boolean(compute='_compute_discount_approval')

    def _compute_discount_approval(self):
        for rec in self:
            if rec.order_line:
                discount_vals = self.order_line.mapped('discount')
                user_discount = self.env.user.allow_discount
                to_approve = False
                for val in discount_vals:
                    if val > user_discount:
                        if rec.state in ['draft', 'waiting_for_approval']:
                            to_approve = True
                            break
                rec.is_discount_approval = to_approve
            else:
                rec.is_discount_approval = False

    def action_view_reject_reasons(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale_order_discount_approval_odoo.action_discount_sale_reject_reason")
        if len(self.reject_reason_ids) > 1:
            action['domain'] = [('sale_order_id', '=', self.id)]
        else:
            action['res_id'] =  self.reject_reason_ids.ids[0]
            action['views'] = [(self.env.ref('sale_order_discount_approval_odoo.view_discount_sale_reject_reason').id, 'form')]
        return action


    def action_send_discount(self):
        to_approve = False
        discount_vals = self.order_line.mapped('discount')
        approval_users = self.env.ref('sale_order_discount_approval_odoo.sale_order_discount_approval_odoo_group_manager').users
        user_discount = self.env.user.allow_discount
        if self.env.user.is_discount_control == True:
            for rec in discount_vals:
                if rec > user_discount:
                    to_approve = True
                    break
        if to_approve:
            action_id = self.env.ref(
                'sale.action_quotations_with_onboarding').id
            redirect_link = f"/web#id={self.id}&cids=1&menu_id=178&action={action_id}" \
                            "&model=sale.order&view_type=form"
            url = self.env['ir.config_parameter'].sudo().get_param(
                'web.base.url') + redirect_link
            mail_body = f"""<p>Hello,</p> <p>New sale order '{self.name}' 
            created with Discount by '{self.env.user.name}' need your approval
             on it.</p> <p>To Approve, Cancel Order, Click on the Following 
             Link: <a href='{url}' style="display: inline-block; 
             padding: 10px; text-decoration: none; font-size: 12px; 
             background-color: #875A7B; color: #fff; border-radius: 5px;
             "><strong>Click Me</strong></a> </p> <p>Thank You.</p>"""
            mail_values = {
                'subject': f"{self.name} Discount Approval Request",
                'body_html': mail_body,
                # 'email_to': user.partner_id.email,
                'recipient_ids': [(6, 0, approval_users.partner_id.ids)],
                'email_from': self.env.user.partner_id.email,
                'model': 'sale.order',
            }
            mail_id = self.env['mail.mail'].sudo().create(mail_values)
            mail_id.send()
            self.state = 'waiting_for_approval'

    def action_waiting_approval(self):
        """Method for approving the sale order discount"""
        self.ensure_one()
        # self.approval_user_id = self.env.user.id
        # self.state = 'sent'
        template_sale = self.env.ref('sale.email_template_edi_sale', raise_if_not_found=False)
        ctx = {
            'default_model': 'sale.order',
            'default_res_ids': self.ids,
            'default_template_id': template_sale.id if template_sale else None,
            'default_email_layout_xmlid': False,
            'default_auto_delete': False,
            'default_force_send': False,
            'proforma': True,
            'set_state': 'sent'
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


    def action_reject(self):
        self.ensure_one()
        reject_reason_id = self.env['discount.reject.reason'].sudo().create({
            'sale_order_id': self.id,
            'reason_created_by': self.env.user.id
        })

        return {
            'type': 'ir.actions.act_window',
            'target': 'new',
            'name': _('Discount Reject Reason'),
            'view_mode': 'form',
            'res_model': 'discount.reject.reason',
            'res_id': reject_reason_id.id,
            'views': [(self.env.ref('sale_order_discount_approval_odoo.view_discount_sale_reject_reason').id, 'form')],
        }


class DiscountRejectReason(models.Model):

    _name = 'discount.reject.reason'
    _description = 'Discount Reject Reason'

    reason = fields.Text('Reason')
    reason_created_by = fields.Many2one('res.users', string='Reject Reason Created By', default=lambda self: self.env.user)
    sale_order_id = fields.Many2one('sale.order')

    def submit_reason(self):

        if not self.reason:
            raise UserError(_("Please Enter Reason!!!!!!"))
        self.sale_order_id.state = 'draft'


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'


    def action_send_mail(self):
        res = super(MailComposeMessage, self).action_send_mail()
        for msg in self:
            if msg._context.get('set_state', False) == 'sent' and msg._context.get('default_model') == 'sale.order':
                sale_order = self.env[msg._context.get('default_model')].sudo().browse(msg._context.get('default_res_ids')[0])
                sale_order.state = msg._context.get('set_state', False)
        return res

