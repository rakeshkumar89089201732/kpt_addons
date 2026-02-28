# -*- coding: utf-8 -*-

from odoo import api, models


class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    def write(self, vals):
        """Sync attachment types when structure rules are updated"""
        result = super().write(vals)
        if 'rule_ids' in vals:
            # Trigger sync when rules are added/removed from structure
            self.env['hr.salary.rule']._sync_attachment_types_from_rules()
        return result
