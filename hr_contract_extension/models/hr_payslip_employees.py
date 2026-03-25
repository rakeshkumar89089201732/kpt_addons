# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.osv import expression


class HrPayslipEmployees(models.TransientModel):
    _inherit = "hr.payslip.employees"

    manager_id = fields.Many2one(
        "hr.employee",
        string="Manager",
        help="Filter employees by their manager (Employee → Manager).",
    )

    @api.depends("department_id", "manager_id")
    def _compute_employee_ids(self):
        for wizard in self:
            domain = wizard._get_available_contracts_domain()
            if wizard.department_id:
                domain = expression.AND(
                    [
                        domain,
                        [("department_id", "child_of", wizard.department_id.id)],
                    ]
                )
            if wizard.manager_id:
                # Include all employees under this manager in the hierarchy.
                domain = expression.AND(
                    [
                        domain,
                        [("parent_id", "child_of", wizard.manager_id.id)],
                    ]
                )
            wizard.employee_ids = self.env["hr.employee"].search(domain)

