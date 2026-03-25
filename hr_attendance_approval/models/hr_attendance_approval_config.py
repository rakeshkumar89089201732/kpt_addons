# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrAttendanceApprovalConfig(models.Model):
    _name = 'hr.attendance.approval.config'
    _description = 'Attendance Approval Configuration'
    _order = 'id desc'

    name = fields.Char(string='Configuration Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    approval_level_ids = fields.One2many(
        'hr.attendance.approval.level',
        'config_id',
        string='Approval Levels'
    )
    department_ids = fields.Many2many(
        'hr.department',
        'hr_attendance_approval_config_department_rel',
        'config_id',
        'department_id',
        string='Departments',
        help='Leave empty to apply to all departments'
    )

    @api.constrains('approval_level_ids')
    def _check_approval_levels(self):
        for config in self:
            if not config.approval_level_ids:
                raise ValidationError(_('At least one approval level is required.'))
            sequences = config.approval_level_ids.mapped('sequence')
            if len(sequences) != len(set(sequences)):
                raise ValidationError(_('Approval level sequences must be unique.'))


class HrAttendanceApprovalLevel(models.Model):
    _name = 'hr.attendance.approval.level'
    _description = 'Attendance Approval Level'
    _order = 'sequence, id'

    name = fields.Char(string='Level Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10, required=True)
    config_id = fields.Many2one(
        'hr.attendance.approval.config',
        string='Configuration',
        required=True,
        ondelete='cascade'
    )
    approver_type = fields.Selection([
        ('manager', 'Direct Manager'),
        ('department_manager', 'Department Manager'),
        ('specific_user', 'Specific User'),
        ('specific_users', 'Specific Users'),
        ('group', 'User Group'),
    ], string='Approver Type', required=True, default='manager')
    user_id = fields.Many2one(
        'res.users',
        string='Specific User',
        help='Required if Approver Type is Specific User'
    )
    approver_user_ids = fields.Many2many(
        'res.users',
        'hr_attendance_approval_level_user_rel',
        'level_id',
        'user_id',
        string='Specific Users',
        help='Required if Approver Type is Specific Users'
    )
    group_id = fields.Many2one(
        'res.groups',
        string='User Group',
        help='Required if Approver Type is User Group'
    )
    can_reject = fields.Boolean(string='Can Reject', default=True)
    notification_template_id = fields.Many2one(
        'mail.template',
        string='Notification Template',
        domain="[('model', '=', 'hr.attendance.approval')]"
    )

    @api.constrains('approver_type', 'user_id', 'approver_user_ids', 'group_id')
    def _check_approver_config(self):
        for level in self:
            if level.approver_type == 'specific_user' and not level.user_id:
                raise ValidationError(_('Please select a specific user for approval level "%s".') % level.name)
            if level.approver_type == 'specific_users' and not level.approver_user_ids:
                raise ValidationError(_('Please select at least one user for approval level "%s".') % level.name)
            if level.approver_type == 'group' and not level.group_id:
                raise ValidationError(_('Please select a user group for approval level "%s".') % level.name)

    def get_approvers(self, employee):
        """Get the approver(s) for this level based on the employee."""
        self.ensure_one()
        if self.approver_type == 'manager':
            if employee.parent_id and employee.parent_id.user_id:
                return employee.parent_id.user_id
        elif self.approver_type == 'department_manager':
            if employee.department_id and employee.department_id.manager_id and employee.department_id.manager_id.user_id:
                return employee.department_id.manager_id.user_id
        elif self.approver_type == 'specific_user':
            return self.user_id
        elif self.approver_type == 'specific_users':
            return self.approver_user_ids
        elif self.approver_type == 'group':
            return self.group_id.users
        return self.env['res.users']
