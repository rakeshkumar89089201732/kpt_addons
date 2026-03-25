from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    purchase_team_id = fields.Many2one(comodel_name="purchase.order.teams", string="Purchase Team")
    purchase_approve_line = fields.One2many(comodel_name="purchase.approve.route", inverse_name="purchase_id")

    @api.model
    def create(self, vals):
        res = super(PurchaseOrder, self).create(vals)
        if res.purchase_team_id:
            for member_id in res.purchase_team_id.team_member:
                self.env["purchase.approve.route"].create({
                    "purchase_id": res.id,
                    "partner_id": member_id.partner_id.id,
                    "role": member_id.role,
                    "state": "draft",
                })
        return res

    def write(self, vals):
        res = super(PurchaseOrder, self).write(vals)
        if 'purchase_team_id' in vals:
            for line_id in self.purchase_approve_line:
                line_id.sudo().unlink()
            if self.purchase_team_id:
                for member_id in self.purchase_team_id.team_member:
                    self.env["purchase.approve.route"].create({
                        "purchase_id": self.id,
                        "partner_id": member_id.partner_id.id,
                        "role": member_id.role,
                        "state": "draft",
                    })
        return res

    def button_confirm(self):
        if self.purchase_approve_line:
            if self.purchase_approve_line.filtered(lambda l: l.state != 'done'):
                raise UserError(_('%s Order is not approved') % self.name)
        return super(PurchaseOrder, self).button_confirm()

    def approve_purchase(self):
        if self.purchase_approve_line:
            if self.purchase_approve_line.filtered(lambda l: l.partner_id.id == self.env.user.partner_id.id):
                for line_id in self.purchase_approve_line.filtered(lambda l: l.partner_id.id == self.env.user.partner_id.id):
                    line_id.write({
                        "state": "done"
                    })
            else:
                raise UserError(_("Sorry, you don't have access for approve %s Order") % self.name)

    def disapprove_purchase(self):
        if self.purchase_approve_line:
            if self.purchase_approve_line.filtered(lambda l: l.partner_id.id == self.env.user.partner_id.id):
                for line_id in self.purchase_approve_line.filtered(lambda l: l.partner_id.id == self.env.user.partner_id.id):
                    line_id.write({
                        "state": "cancel"
                    })
            else:
                raise UserError(_("Sorry, you don't have access for cancel %s Order") % self.name)
