# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    offer_count = fields.Integer(
        string='Offer Count',
        compute='_compute_offer_count',
    )
    offer_ids = fields.One2many(
        'employee.offer',
        'employee_id',
        string='Offers',
    )

    @api.depends('offer_ids')
    def _compute_offer_count(self):
        for employee in self:
            employee.offer_count = len(employee.offer_ids)
