# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def _get_access_group_selection(self):
        """Return selection options: Administrator, Employee own data, Manager team data"""
        admin_group = self.env.ref('base.group_system', raise_if_not_found=False)
        employee_own_group = self.env.ref('manager_team_access.group_employee_own_access', raise_if_not_found=False)
        manager_team_group = self.env.ref('manager_team_access.group_manager_team_access', raise_if_not_found=False)
        
        selection = []
        if admin_group:
            selection.append((str(admin_group.id), 'Administrator'))
        if employee_own_group:
            selection.append((str(employee_own_group.id), 'Employee own data'))
        if manager_team_group:
            selection.append((str(manager_team_group.id), 'Manager team data'))
        
        return selection

    # HR Module Access Groups - Only three options: Administrator, Employee own data, Manager team data
    hr_employee_access_group = fields.Selection(
        selection='_get_access_group_selection',
        string='Employees',
        help="Select access group for Employees module. Administrator can see all, Employee own data shows only own records, Manager team data shows own and subordinates.",
    )
    hr_contract_access_group = fields.Selection(
        selection='_get_access_group_selection',
        string='Contracts',
        help="Select access group for Contracts module.",
    )
    hr_attendance_access_group = fields.Selection(
        selection='_get_access_group_selection',
        string='Attendances',
        help="Select access group for Attendances module.",
    )
    hr_leave_access_group = fields.Selection(
        selection='_get_access_group_selection',
        string='Time Off',
        help="Select access group for Time Off module.",
    )
    hr_expense_access_group = fields.Selection(
        selection='_get_access_group_selection',
        string='Expenses',
        help="Select access group for Expenses module.",
    )
    hr_payroll_access_group = fields.Selection(
        selection='_get_access_group_selection',
        string='Payroll',
        help="Select access group for Payroll module.",
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        # Get default groups - default to Administrator (all access)
        admin_group = self.env.ref('base.group_system', raise_if_not_found=False)
        admin_id = str(admin_group.id) if admin_group else False
        
        # Get stored values from config parameters, default to Administrator
        res.update({
            'hr_employee_access_group': self.env['ir.config_parameter'].sudo().get_param('manager_team_access.hr_employee_access_group', admin_id),
            'hr_contract_access_group': self.env['ir.config_parameter'].sudo().get_param('manager_team_access.hr_contract_access_group', admin_id),
            'hr_attendance_access_group': self.env['ir.config_parameter'].sudo().get_param('manager_team_access.hr_attendance_access_group', admin_id),
            'hr_leave_access_group': self.env['ir.config_parameter'].sudo().get_param('manager_team_access.hr_leave_access_group', admin_id),
            'hr_expense_access_group': self.env['ir.config_parameter'].sudo().get_param('manager_team_access.hr_expense_access_group', admin_id),
            'hr_payroll_access_group': self.env['ir.config_parameter'].sudo().get_param('manager_team_access.hr_payroll_access_group', admin_id),
        })
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        # Store values in config parameters
        self.env['ir.config_parameter'].sudo().set_param('manager_team_access.hr_employee_access_group', self.hr_employee_access_group or '')
        self.env['ir.config_parameter'].sudo().set_param('manager_team_access.hr_contract_access_group', self.hr_contract_access_group or '')
        self.env['ir.config_parameter'].sudo().set_param('manager_team_access.hr_attendance_access_group', self.hr_attendance_access_group or '')
        self.env['ir.config_parameter'].sudo().set_param('manager_team_access.hr_leave_access_group', self.hr_leave_access_group or '')
        self.env['ir.config_parameter'].sudo().set_param('manager_team_access.hr_expense_access_group', self.hr_expense_access_group or '')
        self.env['ir.config_parameter'].sudo().set_param('manager_team_access.hr_payroll_access_group', self.hr_payroll_access_group or '')
