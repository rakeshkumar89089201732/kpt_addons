# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.addons.base.models.res_users import name_selection_groups


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _get_employee_for_restriction(self):
        """Return the current user's employee record (for own/team restriction). Uses fallbacks if employee_id not set."""
        self.ensure_one()
        employee = self.employee_id
        if not employee:
            employee = self.env['hr.employee'].sudo().search([
                ('user_id', '=', self.id),
                ('company_id', 'in', self.env.companies.ids),
            ], limit=1)
        if not employee and self.partner_id:
            employee = self.env['hr.employee'].sudo().search([
                ('work_contact_id', '=', self.partner_id.id),
                ('company_id', 'in', self.env.companies.ids),
            ], limit=1)
        return employee

    def _get_restricted_employee_ids(self):
        """
        Return employee ids the current user is allowed to see for HR record rules:
        - Manager (Team Data Only): own + all subordinates.
        - Employee (Own Data Only): own only.
        - Neither group: None (no restriction).
        """
        self.ensure_one()
        if self.has_group('manager_team_access.group_manager_team_access'):
            employee = self._get_employee_for_restriction()
            if not employee:
                return []
            allowed = employee._get_subordinate_employee_ids()
            company_ids = self.env.companies.ids
            allowed = allowed.filtered(lambda e: e.company_id.id in company_ids)
            return allowed.ids
        if self.has_group('manager_team_access.group_employee_own_access'):
            employee = self._get_employee_for_restriction()
            if not employee:
                return []
            return employee.ids
        return None

    def _get_manager_team_employee_ids(self):
        """Kept for backward compatibility; use _get_restricted_employee_ids() in ir_rule."""
        return self._get_restricted_employee_ids()

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """Override to ensure HR module group selection fields always have valid metadata."""
        res = super(ResUsers, self).fields_get(allfields=allfields, attributes=attributes)
        
        # Ensure all selection group fields have proper type metadata
        # This prevents SearchArchParser errors when fields are referenced
        for field_name in list(res.keys()):
            if field_name.startswith('sel_groups_'):
                field_info = res[field_name]
                # Ensure type is always present
                if 'type' not in field_info:
                    res[field_name]['type'] = 'selection'
                # Ensure selection list is always valid (not empty or None)
                if field_info.get('type') == 'selection':
                    if 'selection' not in field_info or not field_info.get('selection'):
                        # If selection is empty or missing, provide default
                        res[field_name]['selection'] = [(False, '')]
                    # Ensure selection is a list of tuples
                    elif not isinstance(field_info.get('selection'), list):
                        res[field_name]['selection'] = [(False, '')]
        
        return res
