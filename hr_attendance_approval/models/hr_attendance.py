# -*- coding: utf-8 -*-

import pytz

from datetime import timedelta

from odoo import models, fields, api


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    worked_hours_edit = fields.Float(
        string='Worked Hours',
        compute='_compute_worked_hours_edit',
        inverse='_inverse_worked_hours_edit',
    )

    attendance_approval_id = fields.Many2one(
        'hr.attendance.approval',
        string='Attendance Approval',
        compute='_compute_attendance_approval_id',
        readonly=True
    )
    approval_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('pending', 'Pending Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Approval Status',
        compute='_compute_attendance_approval_id',
        readonly=True
    )

    @api.depends('employee_id', 'check_in', 'check_out')
    def _compute_attendance_approval_id(self):
        Approval = self.env['hr.attendance.approval']
        for attendance in self:
            attendance.attendance_approval_id = False
            attendance.approval_state = False
            if not attendance.employee_id:
                continue

            approval_date = attendance._get_attendance_approval_date()
            if not approval_date:
                continue

            approval = Approval.search([
                ('employee_id', '=', attendance.employee_id.id),
                ('attendance_date', '=', approval_date),
            ], limit=1)
            attendance.attendance_approval_id = approval
            attendance.approval_state = approval.state if approval else False

    @api.depends('check_in', 'check_out')
    def _compute_worked_hours_edit(self):
        for attendance in self:
            if attendance.check_in and attendance.check_out:
                delta = attendance.check_out - attendance.check_in
                attendance.worked_hours_edit = delta.total_seconds() / 3600.0
            else:
                attendance.worked_hours_edit = 0.0

    def _inverse_worked_hours_edit(self):
        for attendance in self:
            if not attendance.check_in:
                continue
            hours = float(attendance.worked_hours_edit or 0.0)
            attendance.check_out = attendance.check_in + timedelta(hours=hours)

    def action_view_attendance_approval(self):
        self.ensure_one()
        if not self.attendance_approval_id:
            return False
        return {
            'name': 'Attendance Approval',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance.approval',
            'view_mode': 'form',
            'res_id': self.attendance_approval_id.id,
            'target': 'current',
        }

    def _get_attendance_approval_date(self):
        self.ensure_one()
        if not self.employee_id or not self.check_in:
            return False
        employee_tz = self.employee_id._get_tz() or 'UTC'
        tz = pytz.timezone(employee_tz)
        check_in_utc = pytz.utc.localize(self.check_in) if not self.check_in.tzinfo else self.check_in.astimezone(pytz.utc)
        return check_in_utc.astimezone(tz).date()

    def _sync_attendance_approval(self):
        Approval = self.env['hr.attendance.approval'].sudo()
        for attendance in self:
            approval_date = attendance._get_attendance_approval_date()
            if not approval_date:
                continue

            approval = Approval.search([
                ('employee_id', '=', attendance.employee_id.id),
                ('attendance_date', '=', approval_date),
            ], limit=1)

            vals = {
                'employee_id': attendance.employee_id.id,
                'attendance_date': approval_date,
                'hr_attendance_id': attendance.id,
            }

            if attendance.check_in:
                vals['check_in'] = attendance.check_in
            if attendance.check_out:
                vals['check_out'] = attendance.check_out

            if approval:
                if attendance.check_in and (not approval.check_in or attendance.check_in < approval.check_in):
                    vals['check_in'] = attendance.check_in
                else:
                    vals.pop('check_in', None)

                if attendance.check_out and (not approval.check_out or attendance.check_out > approval.check_out):
                    vals['check_out'] = attendance.check_out
                else:
                    vals.pop('check_out', None)

                vals['hr_attendance_id'] = attendance.id

                if vals:
                    approval.write(vals)
            else:
                approval = Approval.create(vals)

            if attendance.check_out and approval.state == 'draft':
                # Auto-submit for approval once employee checks out.
                # Do not raise if configuration is missing; keep it in pending without activities.
                approval.write({'state': 'pending', 'current_approval_level': 0})
                if approval.approval_config_id and approval.next_approver_ids:
                    approval._create_approval_activity()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_attendance_approval()
        return records

    def write(self, vals):
        res = super().write(vals)
        if {'employee_id', 'check_in', 'check_out'} & set(vals.keys()):
            self._sync_attendance_approval()
        return res
