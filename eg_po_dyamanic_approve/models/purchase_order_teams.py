from odoo import models, fields


class PurchaseOrderTeams(models.Model):
    _name = "purchase.order.teams"
    _description = "Purchase Order Teams"

    name = fields.Char(string="Name")
    team_lead_id = fields.Many2one(comodel_name="res.partner", string="Team Lead")
    team_member = fields.One2many(comodel_name="purchase.team.member", inverse_name="purchase_team_id", string="Team Member")