# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class HrAttendanceApproval(models.Model):
    _name = 'hr.attendance.approval'
    _description = 'HR Attendance Approval'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'attendance_date desc, id desc'
    _rec_name = 'display_name'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        tracking=True,
        default=lambda self: self.env.user.employee_id
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='employee_id.department_id',
        store=True
    )
    manager_id = fields.Many2one(
        'hr.employee',
        string='Manager',
        related='employee_id.parent_id',
        store=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='employee_id.company_id',
        store=True
    )
    attendance_date = fields.Date(
        string='Attendance Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    check_in = fields.Datetime(
        string='Check In',
        tracking=True
    )
    check_out = fields.Datetime(
        string='Check Out',
        tracking=True
    )
    worked_hours = fields.Float(
        string='Worked Hours',
        compute='_compute_worked_hours',
        store=True
    )
    hr_attendance_id = fields.Many2one(
        'hr.attendance',
        string='Linked Attendance',
        readonly=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True, required=True)
    
    approval_config_id = fields.Many2one(
        'hr.attendance.approval.config',
        string='Approval Configuration',
        compute='_compute_approval_config',
        store=True
    )
    current_approval_level = fields.Integer(
        string='Current Approval Level',
        default=0
    )
    approval_line_ids = fields.One2many(
        'hr.attendance.approval.line',
        'attendance_approval_id',
        string='Approval History'
    )
    next_approver_ids = fields.Many2many(
        'res.users',
        'hr_attendance_approval_next_approver_rel',
        'approval_id',
        'user_id',
        string='Next Approvers',
        compute='_compute_next_approvers',
        store=True
    )
    can_approve = fields.Boolean(
        string='Can Approve',
        compute='_compute_can_approve'
    )
    rejection_reason = fields.Text(string='Rejection Reason')
    notes = fields.Text(string='Notes')
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )

    _sql_constraints = [
        ('unique_employee_date', 'unique(employee_id, attendance_date)',
         'An attendance record already exists for this employee on this date!')
    ]

    @api.depends('employee_id', 'attendance_date')
    def _compute_display_name(self):
        for record in self:
            if record.employee_id and record.attendance_date:
                record.display_name = f"{record.employee_id.name} - {record.attendance_date}"
            else:
                record.display_name = _('New Attendance')

    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):
        for record in self:
            if record.check_in and record.check_out:
                delta = record.check_out - record.check_in
                record.worked_hours = delta.total_seconds() / 3600.0
            else:
                record.worked_hours = 0.0

    @api.depends('employee_id', 'department_id')
    def _compute_approval_config(self):
        for record in self:
            Config = self.env['hr.attendance.approval.config']
            config = Config.browse()

            # Prefer a department-specific configuration when available.
            # If none matches, fall back to the global/default configuration
            # (department_ids is empty), which should apply to all employees.
            if record.department_id:
                config = Config.search([
                    ('active', '=', True),
                    ('company_id', '=', record.company_id.id),
                    ('department_ids', 'in', record.department_id.ids),
                ], limit=1)

            if not config:
                config = Config.search([
                    ('active', '=', True),
                    ('company_id', '=', record.company_id.id),
                    ('department_ids', '=', False),
                ], limit=1)

            record.approval_config_id = config

    @api.depends('current_approval_level', 'approval_config_id', 'employee_id', 'state')
    def _compute_next_approvers(self):
        for record in self:
            if record.state not in ('draft', 'pending'):
                record.next_approver_ids = False
                continue
            
            if not record.approval_config_id or not record.approval_config_id.approval_level_ids:
                record.next_approver_ids = False
                continue
            
            levels = record.approval_config_id.approval_level_ids.sorted('sequence')
            if record.current_approval_level < len(levels):
                current_level = levels[record.current_approval_level]
                approvers = current_level.get_approvers(record.employee_id)
                record.next_approver_ids = approvers
            else:
                record.next_approver_ids = False

    @api.depends('next_approver_ids', 'state')
    def _compute_can_approve(self):
        current_user = self.env.user
        for record in self:
            if record.state != 'pending':
                record.can_approve = False
            elif current_user.has_group('hr_attendance_approval.group_attendance_approval_admin'):
                record.can_approve = True
            elif current_user in record.next_approver_ids:
                record.can_approve = True
            else:
                record.can_approve = False

    @api.constrains('check_in', 'check_out')
    def _check_validity(self):
        for record in self:
            if record.check_in and record.check_out:
                if record.check_out < record.check_in:
                    raise ValidationError(_('Check Out time cannot be earlier than Check In time.'))

    def action_check_in(self):
        """Employee check-in action."""
        self.ensure_one()
        if self.check_in:
            raise UserError(_('You have already checked in for this date.'))
        self.check_in = fields.Datetime.now()
        self.message_post(body=_('Employee checked in at %s') % self.check_in)

    def action_check_out(self):
        """Employee check-out action."""
        self.ensure_one()
        if not self.check_in:
            raise UserError(_('Please check in first.'))
        if self.check_out:
            raise UserError(_('You have already checked out for this date.'))
        self.check_out = fields.Datetime.now()
        self.message_post(body=_('Employee checked out at %s') % self.check_out)

    def action_submit(self):
        """Submit attendance for approval."""
        for record in self:
            if not record.check_in:
                raise UserError(_('Please check in before submitting for approval.'))
            if not record.approval_config_id:
                raise UserError(_('No approval configuration found. Please contact your administrator.'))
            record.write({
                'state': 'pending',
                'current_approval_level': 0
            })
            record._create_approval_activity()
            record.message_post(body=_('Attendance submitted for approval.'))

    def action_approve(self):
        """Approve attendance at current level."""
        self.ensure_one()
        if not self.can_approve:
            raise UserError(_('You are not authorized to approve this attendance.'))
        
        # Create approval line
        self.env['hr.attendance.approval.line'].create({
            'attendance_approval_id': self.id,
            'user_id': self.env.user.id,
            'action': 'approve',
            'level_sequence': self.current_approval_level,
            'notes': ''
        })
        
        # Check if there are more approval levels
        levels = self.approval_config_id.approval_level_ids.sorted('sequence')
        next_level = self.current_approval_level + 1
        
        if next_level >= len(levels):
            # All levels approved, mark as approved
            self.write({
                'state': 'approved',
                'current_approval_level': next_level
            })
            self._create_hr_attendance()

            # If payroll/work entries are installed, ensure work entries exist for the approved attendance.
            # This makes the approved attendance usable for payslip generation.
            if self.hr_attendance_id:
                WorkEntry = False
                try:
                    WorkEntry = self.env['hr.work.entry']
                except KeyError:
                    WorkEntry = False

                if WorkEntry:
                    # Reuse the same error-checking context expected by hr_work_entry.
                    att = self.hr_attendance_id.sudo()
                    start = att.check_in
                    stop = att.check_out
                    if start and stop:
                        with WorkEntry._error_checking(start=start, stop=stop, employee_ids=att.employee_id.ids):
                            att._create_work_entries()

            self.message_post(body=_('Attendance approved by %s. Final approval completed.') % self.env.user.name)
        else:
            # Move to next level
            self.write({
                'current_approval_level': next_level
            })
            self._create_approval_activity()
            self.message_post(body=_('Attendance approved by %s. Moved to next approval level.') % self.env.user.name)
        
        # Mark activities as done
        self.activity_ids.filtered(lambda a: a.user_id == self.env.user).action_done()

    def action_reject(self):
        """Open rejection wizard."""
        self.ensure_one()
        if not self.can_approve:
            raise UserError(_('You are not authorized to reject this attendance.'))
        
        return {
            'name': _('Reject Attendance'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance.rejection.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_attendance_approval_id': self.id,
            }
        }

    def action_reset_to_draft(self):
        """Reset to draft state."""
        for record in self:
            # If approval records are created from default hr.attendance check-in/out,
            # we must not delete the real attendance record.
            record.write({
                'state': 'draft',
                'current_approval_level': 0,
                'rejection_reason': False
            })
            record.approval_line_ids.unlink()
            record.activity_ids.unlink()
            record.message_post(body=_('Attendance reset to draft.'))

    def _create_hr_attendance(self):
        """Create HR Attendance record after full approval."""
        self.ensure_one()
        # When using default Odoo attendance check-in/out, the hr.attendance record already exists.
        # Keep backward compatibility: if hr_attendance_id is set, do not create a duplicate.
        if self.hr_attendance_id:
            return
        
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee_id.id,
            'check_in': self.check_in,
            'check_out': self.check_out,
        })
        self.hr_attendance_id = attendance

    def _create_approval_activity(self):
        """Create activity for next approvers."""
        self.ensure_one()
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type:
            return
        
        for approver in self.next_approver_ids:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=approver.id,
                summary=_('Attendance Approval Required'),
                note=_('Please review and approve the attendance for %s on %s') % (
                    self.employee_id.name, self.attendance_date
                )
            )

    @api.model
    def get_my_attendances_to_approve(self):
        """Get attendances pending approval for current user."""
        current_user = self.env.user
        if current_user.has_group('hr_attendance_approval.group_attendance_approval_admin'):
            return self.search([('state', '=', 'pending')])
        return self.search([
            ('state', '=', 'pending'),
            ('next_approver_ids', 'in', current_user.ids)
        ])

    @api.model
    def create_today_attendance(self):
        """Create attendance record for today if not exists."""
        employee = self.env.user.employee_id
        if not employee:
            raise UserError(_('No employee record found for current user.'))
        
        today = fields.Date.context_today(self)
        existing = self.search([
            ('employee_id', '=', employee.id),
            ('attendance_date', '=', today)
        ], limit=1)
        
        if existing:
            return existing
        
        return self.create({
            'employee_id': employee.id,
            'attendance_date': today,
        })


class HrAttendanceApprovalLine(models.Model):
    _name = 'hr.attendance.approval.line'
    _description = 'Attendance Approval Line'
    _order = 'create_date desc'

    attendance_approval_id = fields.Many2one(
        'hr.attendance.approval',
        string='Attendance Approval',
        required=True,
        ondelete='cascade'
    )
    user_id = fields.Many2one(
        'res.users',
        string='Approver',
        required=True,
        default=lambda self: self.env.user
    )
    action = fields.Selection([
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
    ], string='Action', required=True)
    level_sequence = fields.Integer(string='Approval Level')
    action_date = fields.Datetime(
        string='Action Date',
        default=fields.Datetime.now,
        required=True
    )
    notes = fields.Text(string='Notes')


class HrAttendanceRejectionWizard(models.TransientModel):
    _name = 'hr.attendance.rejection.wizard'
    _description = 'Attendance Rejection Wizard'

    attendance_approval_id = fields.Many2one(
        'hr.attendance.approval',
        string='Attendance Approval',
        required=True
    )
    rejection_reason = fields.Text(
        string='Rejection Reason',
        required=True
    )

    def action_reject(self):
        """Execute rejection."""
        self.ensure_one()
        approval = self.attendance_approval_id
        
        # Create rejection line
        self.env['hr.attendance.approval.line'].create({
            'attendance_approval_id': approval.id,
            'user_id': self.env.user.id,
            'action': 'reject',
            'level_sequence': approval.current_approval_level,
            'notes': self.rejection_reason
        })
        
        approval.write({
            'state': 'rejected',
            'rejection_reason': self.rejection_reason
        })
        
        approval.message_post(body=_('Attendance rejected by %s. Reason: %s') % (
            self.env.user.name, self.rejection_reason
        ))
        
        # Mark activities as done
        approval.activity_ids.filtered(lambda a: a.user_id == self.env.user).action_done()
        
        return {'type': 'ir.actions.act_window_close'}
