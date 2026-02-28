# -*- coding: utf-8 -*-
from odoo import api, fields, models


class EmployeeSalarySheetWizard(models.TransientModel):
    _name = 'employee.salary.sheet.wizard'
    _description = 'Employee Salary Sheet'

    employee_id = fields.Many2one('hr.employee', required=True, readonly=True)

    salary_sheet_attachment_count = fields.Integer(
        string='Salary Sheets',
        compute='_compute_salary_sheet_attachment_count'
    )

    @api.depends('employee_id')
    def _compute_salary_sheet_attachment_count(self):
        Attachment = self.env['ir.attachment']
        for wiz in self:
            if not wiz.employee_id:
                wiz.salary_sheet_attachment_count = 0
                continue
            wiz.salary_sheet_attachment_count = Attachment.search_count([
                ('res_model', '=', 'hr.employee'),
                ('res_id', '=', wiz.employee_id.id),
                ('mimetype', '=', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ])

    def action_generate(self):
        self.ensure_one()
        return self.employee_id.action_open_salary_sheet_wizard()

    def action_open_saved(self):
        self.ensure_one()
        return self.employee_id.action_open_salary_sheet_attachments()
