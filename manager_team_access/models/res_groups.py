# -*- coding: utf-8 -*-
import logging
from odoo import models, api
from collections import defaultdict

_logger = logging.getLogger(__name__)


class ResGroups(models.Model):
    _inherit = 'res.groups'

    @api.model
    def get_groups_by_application(self):
        """Override to filter HR module groups to only show Administrator, Employee own data, and Manager team data."""
        res = super(ResGroups, self).get_groups_by_application()
        
        # Only filter if module is installed and groups exist
        # Check if our module is installed by trying to find one of our groups
        try:
            test_group = self.env.ref('manager_team_access.group_employee_own_access', raise_if_not_found=False)
            if not test_group:
                # Module not installed or groups don't exist yet, return original
                return res
        except Exception:
            # If we can't check, be safe and return original
            return res
        
        # HR module subcategories that should be restricted (using exact category XML IDs)
        hr_subcategories = [
            'base.module_category_human_resources_employees',  # Employees
            'base.module_category_human_resources_contracts',  # Contracts
            'base.module_category_human_resources_attendances',  # Attendances (note: with 's')
            'base.module_category_human_resources_time_off',  # Time Off
            'base.module_category_human_resources_expenses',  # Expenses (note: with 's')
            'base.module_category_human_resources_payroll',  # Payroll
        ]
        
        # Map subcategories to their corresponding custom groups
        subcategory_group_map = {
            'base.module_category_human_resources_employees': {
                'employee': 'manager_team_access.group_employee_own_access_employees',
                'manager': 'manager_team_access.group_manager_team_access_employees',
            },
            'base.module_category_human_resources_contracts': {
                'employee': 'manager_team_access.group_employee_own_access_contracts',
                'manager': 'manager_team_access.group_manager_team_access_contracts',
            },
            'base.module_category_human_resources_attendances': {
                'employee': 'manager_team_access.group_employee_own_access_attendance',
                'manager': 'manager_team_access.group_manager_team_access_attendance',
            },
            'base.module_category_human_resources_time_off': {
                'employee': 'manager_team_access.group_employee_own_access_time_off',
                'manager': 'manager_team_access.group_manager_team_access_time_off',
            },
            'base.module_category_human_resources_expenses': {
                'employee': 'manager_team_access.group_employee_own_access_expense',
                'manager': 'manager_team_access.group_manager_team_access_expense',
            },
            'base.module_category_human_resources_payroll': {
                'employee': 'manager_team_access.group_employee_own_access_payroll',
                'manager': 'manager_team_access.group_manager_team_access_payroll',
            },
        }
        
        # Filter the results
        filtered_res = []
        for app, kind, gs, category_name in res:
            if app.xml_id in hr_subcategories and kind == 'selection':
                try:
                    # For each HR category, we want to show only:
                    # 1. Administrator (the existing admin group in that category)
                    # 2. Employee own data (our custom group for this subcategory)
                    # 3. Manager team data (our custom group for this subcategory)
                    
                    # Find the administrator group in this category (usually the one with 'Administrator' in name)
                    admin_group = gs.filtered(lambda g: 'Administrator' in g.name)
                    
                    # Get the custom groups for this subcategory
                    group_refs = subcategory_group_map.get(app.xml_id, {})
                    employee_own_group = False
                    manager_team_group = False
                    
                    if group_refs.get('employee'):
                        try:
                            employee_own_group = self.env.ref(group_refs.get('employee'), raise_if_not_found=False)
                        except Exception:
                            employee_own_group = False
                    
                    if group_refs.get('manager'):
                        try:
                            manager_team_group = self.env.ref(group_refs.get('manager'), raise_if_not_found=False)
                        except Exception:
                            manager_team_group = False
                    
                    # Build allowed groups list - always include admin + our two custom groups
                    allowed_gs = self.env['res.groups']
                    if admin_group:
                        allowed_gs |= admin_group
                    if employee_own_group:
                        allowed_gs |= employee_own_group
                    if manager_team_group:
                        allowed_gs |= manager_team_group
                    
                    # Only replace if we have at least the admin group and at least one other group
                    # This ensures field names remain stable and we don't break views
                    if allowed_gs and len(allowed_gs) >= 2 and admin_group:
                        # Sort groups to ensure consistent field names (admin first, then our custom groups)
                        sorted_groups = admin_group.sorted('id')
                        if employee_own_group:
                            sorted_groups |= employee_own_group.sorted('id')
                        if manager_team_group:
                            sorted_groups |= manager_team_group.sorted('id')
                        filtered_res.append((app, kind, sorted_groups, category_name))
                    else:
                        # Fallback: keep original if we couldn't find enough groups
                        # This prevents breaking existing views
                        filtered_res.append((app, kind, gs, category_name))
                except Exception as e:
                    # If anything goes wrong, keep original groups to prevent breaking views
                    _logger.warning("Error filtering HR groups for %s: %s", app.xml_id, str(e))
                    filtered_res.append((app, kind, gs, category_name))
            else:
                # Keep non-HR categories as-is
                filtered_res.append((app, kind, gs, category_name))
        
        return filtered_res
