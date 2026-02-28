# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.osv import expression


class IrRule(models.Model):
    _inherit = 'ir.rule'

    @api.model
    def _compute_domain(self, model_name, mode='read'):
        res = super()._compute_domain(model_name, mode)
        if self.env.su:
            return res
        # Apply restriction for Manager (Team Data Only) or Employee (Own Data Only)
        has_restriction = (
            self.env.user.has_group('manager_team_access.group_manager_team_access')
            or self.env.user.has_group('manager_team_access.group_employee_own_access')
        )
        if not has_restriction:
            return res

        allowed_employee_ids = self.env.user._get_restricted_employee_ids()
        if allowed_employee_ids is None:
            return res

        # Directory uses hr.employee.public (same ids as hr.employee); apply same restriction with or without a rule
        if model_name == 'hr.employee.public':
            if not allowed_employee_ids:
                return expression.AND([res, [('id', '=', False)]])
            return expression.AND([res, [('id', 'in', allowed_employee_ids)]])

        Rule = self.env['manager.team.access.rule'].sudo()
        rules = Rule.search([
            ('model_id.model', '=', model_name),
            ('active', '=', True),
            '|',
            ('company_id', '=', False),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        if not rules:
            return res

        rule = rules[0]
        if not rule.include_own and not rule.include_team:
            return expression.AND([res, [('id', '=', False)]])

        if model_name == 'hr.employee':
            if not allowed_employee_ids:
                domain = [('id', '=', False)]
            else:
                domain = [('id', 'in', allowed_employee_ids)]
        elif model_name == 'res.partner':
            if not allowed_employee_ids:
                # No employee linked: keep internal users' partners visible to avoid breaking core flows
                domain = [('partner_share', '=', False)]
            else:
                employees = self.env['hr.employee'].sudo().browse(allowed_employee_ids)
                partner_ids = employees.mapped('work_contact_id').filtered(lambda p: p).ids
                # Manager sees only: own partner + team work contacts (so Contacts app shows their team only)
                # Keep internal users' partners so user/company dropdowns and chatter still work
                domain = expression.OR([
                    [('partner_share', '=', False)],
                    [('id', '=', self.env.user.partner_id.id)],
                    [('id', 'in', partner_ids)] if partner_ids else [('id', '=', False)],
                ])
        else:
            field = rule.employee_field or 'employee_id'
            domain = [(field, 'in', allowed_employee_ids)] if allowed_employee_ids else [(field, '=', False)]

        return expression.AND([res, domain])
