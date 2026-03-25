# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    attendance_approval_ids = fields.One2many(
        'hr.attendance.approval',
        'employee_id',
        string='Attendance Approvals'
    )
    attendance_approval_count = fields.Integer(
        string='Attendance Approvals',
        compute='_compute_attendance_approval_count'
    )
    pending_attendance_count = fields.Integer(
        string='Pending Approvals',
        compute='_compute_attendance_approval_count'
    )

    def _compute_attendance_approval_count(self):
        AttendanceApproval = self.env['hr.attendance.approval']
        for employee in self:
            employee.attendance_approval_count = AttendanceApproval.search_count([
                ('employee_id', '=', employee.id)
            ])
            employee.pending_attendance_count = AttendanceApproval.search_count([
                ('employee_id', '=', employee.id),
                ('state', '=', 'pending')
            ])

    def action_view_attendance_approvals(self):
        """Open attendance approvals for this employee."""
        self.ensure_one()
        return {
            'name': _('Attendance Approvals'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance.approval',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id}
        }
