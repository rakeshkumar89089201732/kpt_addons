# -*- coding: utf-8 -*-
from odoo import models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def _get_subordinate_employee_ids(self):
        """Return recordset of self + all direct and indirect subordinates (recursive child_ids).
        Uses sudo() so hierarchy is read without triggering our own hr.employee record rule (avoids
        recursion and ensures we get full tree for manager team computation).
        """
        self.ensure_one()
        current = self.sudo()
        all_ids = list(current.ids)
        while current:
            children = current.child_ids.filtered(lambda e: e.id not in all_ids)
            if not children:
                break
            all_ids.extend(children.ids)
            current = children
        return self.browse(all_ids)
