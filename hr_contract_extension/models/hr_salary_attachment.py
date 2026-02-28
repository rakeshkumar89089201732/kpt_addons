# -*- coding: utf-8 -*-

from odoo import api, fields, models


class HrSalaryAttachment(models.Model):
    _inherit = 'hr.salary.attachment'

    category = fields.Selection(
        selection=[
            ('deduction', 'Deduction'),
            ('allowance', 'Allowance'),
        ],
        string='Category',
        related='deduction_type_id.category',
        store=True,
        readonly=True,
        help='Category of this salary attachment'
    )

    def _get_active_amount(self):
        """Compatibility helper for databases where hr_payroll does not define this.
        Returns the sum of active_amount over the recordset, matching the behavior
        of newer enterprise versions.
        """
        return sum(self.mapped('active_amount'))
