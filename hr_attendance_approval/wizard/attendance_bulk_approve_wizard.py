# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrAttendanceBulkApproveWizard(models.TransientModel):
    _name = 'hr.attendance.bulk.approve.wizard'
    _description = 'Bulk Approve Attendance Wizard'

    attendance_approval_ids = fields.Many2many(
        'hr.attendance.approval',
        'hr_attendance_bulk_approve_wizard_rel',
        'wizard_id',
        'attendance_approval_id',
        string='Attendance Records'
    )
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    employee_ids = fields.Many2many(
        'hr.employee',
        'hr_attendance_bulk_approve_employee_rel',
        'wizard_id',
        'employee_id',
        string='Employees'
    )
    department_id = fields.Many2one('hr.department', string='Department')
    pending_count = fields.Integer(
        string='Pending Records',
        compute='_compute_pending_count'
    )
    action_type = fields.Selection([
        ('approve_all', 'Approve All Pending'),
        ('approve_selected', 'Approve Selected Records'),
    ], string='Action Type', default='approve_all', required=True)

    @api.depends('attendance_approval_ids', 'date_from', 'date_to', 'employee_ids', 'department_id', 'action_type')
    def _compute_pending_count(self):
        for wizard in self:
            if wizard.action_type == 'approve_selected':
                wizard.pending_count = len(wizard.attendance_approval_ids.filtered(
                    lambda r: r.state == 'pending' and r.can_approve
                ))
            else:
                records = wizard._get_pending_records()
                wizard.pending_count = len(records)

    def _get_pending_records(self):
        """Get pending attendance records based on filters."""
        domain = [
            ('state', '=', 'pending'),
        ]
        
        if self.date_from:
            domain.append(('attendance_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('attendance_date', '<=', self.date_to))
        if self.employee_ids:
            domain.append(('employee_id', 'in', self.employee_ids.ids))
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        
        records = self.env['hr.attendance.approval'].search(domain)
        # Filter to only records the current user can approve
        return records.filtered(lambda r: r.can_approve)

    def action_approve_all(self):
        """Approve all filtered pending attendance records."""
        self.ensure_one()
        
        if self.action_type == 'approve_selected':
            records = self.attendance_approval_ids.filtered(
                lambda r: r.state == 'pending' and r.can_approve
            )
        else:
            records = self._get_pending_records()
        
        if not records:
            raise UserError(_('No pending attendance records found to approve.'))
        
        approved_count = 0
        failed_records = []
        
        for record in records:
            try:
                record.action_approve()
                approved_count += 1
            except Exception as e:
                failed_records.append({
                    'record': record,
                    'error': str(e)
                })
        
        message = _('%d attendance record(s) approved successfully.') % approved_count
        if failed_records:
            message += _('\n%d record(s) failed to approve.') % len(failed_records)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Bulk Approval Complete'),
                'message': message,
                'type': 'success' if not failed_records else 'warning',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        
        # If called from tree view with selected records
        active_ids = self.env.context.get('active_ids', [])
        if active_ids and 'attendance_approval_ids' in fields_list:
            res['attendance_approval_ids'] = [(6, 0, active_ids)]
            res['action_type'] = 'approve_selected'
        
        return res


class HrAttendanceBulkRejectWizard(models.TransientModel):
    _name = 'hr.attendance.bulk.reject.wizard'
    _description = 'Bulk Reject Attendance Wizard'

    attendance_approval_ids = fields.Many2many(
        'hr.attendance.approval',
        'hr_attendance_bulk_reject_wizard_rel',
        'wizard_id',
        'attendance_approval_id',
        string='Attendance Records'
    )
    rejection_reason = fields.Text(
        string='Rejection Reason',
        required=True
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        if active_ids and 'attendance_approval_ids' in fields_list:
            res['attendance_approval_ids'] = [(6, 0, active_ids)]
        return res

    def action_reject_all(self):
        """Reject all selected attendance records."""
        self.ensure_one()
        
        records = self.attendance_approval_ids.filtered(
            lambda r: r.state == 'pending' and r.can_approve
        )
        
        if not records:
            raise UserError(_('No pending attendance records found to reject.'))
        
        rejected_count = 0
        for record in records:
            try:
                # Create rejection line
                self.env['hr.attendance.approval.line'].create({
                    'attendance_approval_id': record.id,
                    'user_id': self.env.user.id,
                    'action': 'reject',
                    'level_sequence': record.current_approval_level,
                    'notes': self.rejection_reason
                })
                
                record.write({
                    'state': 'rejected',
                    'rejection_reason': self.rejection_reason
                })
                
                record.message_post(body=_('Attendance rejected by %s (Bulk). Reason: %s') % (
                    self.env.user.name, self.rejection_reason
                ))
                
                # Mark activities as done
                record.activity_ids.filtered(lambda a: a.user_id == self.env.user).action_done()
                rejected_count += 1
            except Exception:
                pass
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Bulk Rejection Complete'),
                'message': _('%d attendance record(s) rejected.') % rejected_count,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
