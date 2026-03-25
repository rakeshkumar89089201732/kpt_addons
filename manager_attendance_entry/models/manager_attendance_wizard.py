# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ManagerAttendanceWizard(models.TransientModel):
    _name = 'manager.attendance.wizard'
    _description = 'Manager Attendance Entry'

    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
        help='Working date for which attendances are managed. '
             'Check In / Check Out use the current time on this date.',
    )
    manager_id = fields.Many2one(
        'hr.employee',
        string='Manager',
        required=True,
        readonly=True,
        default=lambda self: self.env.user.employee_id,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='manager_id.company_id',
        store=True,
        readonly=True,
    )
    line_ids = fields.One2many(
        'manager.attendance.line',
        'wizard_id',
        string='Employees',
    )
    
    # Counters
    present_count = fields.Integer(compute='_compute_counts', string="Present")
    absent_count = fields.Integer(compute='_compute_counts', string="Absent")
    
    # Search
    search_query = fields.Char(string='Search Employee')

    @api.depends('line_ids.status')
    def _compute_counts(self):
        for wizard in self:
            wizard.present_count = sum(1 for line in wizard.line_ids if line.status == 'checked_in')
            wizard.absent_count = sum(1 for line in wizard.line_ids if line.status == 'checked_out')

    @api.onchange('search_query')
    def _onchange_search_query(self):
        """Filter lines based on search query."""
        if not self.search_query:
            self._load_employee_lines()
            return

        # Simple case-insensitive search
        query = self.search_query.lower()
        self._load_employee_lines()  # Reset first
        
        # Filter the loaded lines
        filtered_lines = [
            (0, 0, {
                'employee_id': line.employee_id.id,
                'status': line.status,
                'attendance_id': line.attendance_id.id,
                'serial_no': line.serial_no, # Preserve serial
            })
            for line in self.line_ids 
            if query in line.employee_id.name.lower()
        ]
        
        self.line_ids = [(5, 0, 0)] + filtered_lines

    @api.model
    def action_open(self):
        """Entry point used by the server action to open the wizard."""
        wizard = self.create({})
        wizard._load_employee_lines()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'manager.attendance.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _load_employee_lines(self):
        """Load employees that report to the manager into the wizard lines."""
        # self.ensure_one() # Removed ensure_one to allow onchange use
        if not self.manager_id:
            # Fallback if manager_id is lost in onchange context
            employee = self.env.user.employee_id
            if not employee:
                 raise UserError(_('The current user is not linked to an employee.'))
            self.manager_id = employee
            
        Employee = self.env['hr.employee']
        Attendance = self.env['hr.attendance']

        employees = Employee.search([
            ('parent_id', '=', self.manager_id.id),
            ('company_id', '=', self.company_id.id),
            ('active', '=', True),
        ])

        line_vals = []
        for index, emp in enumerate(employees, start=1):
            open_att = Attendance.search([
                ('employee_id', '=', emp.id),
                ('check_out', '=', False),
            ], order='check_in desc', limit=1)

            status = 'checked_in' if open_att else 'checked_out'
            line_vals.append((0, 0, {
                'employee_id': emp.id,
                'status': status,
                'attendance_id': open_att.id or False,
                'serial_no': index,
            }))

        # Reset any existing lines and replace with current snapshot
        self.line_ids = [(5, 0, 0)] + line_vals


class ManagerAttendanceLine(models.TransientModel):
    _name = 'manager.attendance.line'
    _description = 'Manager Attendance Line'

    wizard_id = fields.Many2one(
        'manager.attendance.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    serial_no = fields.Integer(string='#', readonly=True)
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        readonly=True,
    )
    status = fields.Selection(
        [
            ('checked_out', 'Checked Out'),
            ('checked_in', 'Checked In'),
        ],
        string='Status',
        default='checked_out',
        readonly=True,
    )
    attendance_id = fields.Many2one(
        'hr.attendance',
        string='Current Attendance',
        readonly=True,
    )
    can_check_in = fields.Boolean(
        string='Can Check In',
        compute='_compute_can_actions',
    )
    can_check_out = fields.Boolean(
        string='Can Check Out',
        compute='_compute_can_actions',
    )

    def _compute_can_actions(self):
        for line in self:
            line.can_check_in = line.status != 'checked_in'
            line.can_check_out = line.status == 'checked_in'

    def _ensure_no_other_open_attendance(self):
        """Safety helper: reuse hr.attendance validation rules."""
        Attendance = self.env['hr.attendance']
        for line in self:
            open_att = Attendance.search([
                ('employee_id', '=', line.employee_id.id),
                ('check_out', '=', False),
            ], limit=1)
            if open_att:
                raise UserError(_(
                    'Employee %(emp)s already has an open attendance starting at %(check_in)s.',
                    emp=line.employee_id.name,
                    check_in=open_att.check_in,
                ))

    def action_manager_check_in(self):
        """Manager triggers a Check In for selected employees."""
        Attendance = self.env['hr.attendance']
        for line in self:
            if not line.can_check_in:
                continue

            line._ensure_no_other_open_attendance()

            att = Attendance.create({
                'employee_id': line.employee_id.id,
                'check_in': fields.Datetime.now(),
                'in_mode': 'manual',
            })
            line.status = 'checked_in'
            line.attendance_id = att.id
        
        # Re-open the wizard to keep it open and refreshed
        wizard = self.mapped('wizard_id')
        if wizard:
            wizard._load_employee_lines()
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'manager.attendance.wizard',
                'res_id': wizard.id,
                'view_mode': 'form',
                'target': 'new',
            }

    def action_manager_check_out(self):
        """Manager triggers a Check Out for selected employees."""
        for line in self:
            if not line.can_check_out:
                continue

            att = line.attendance_id
            if not att or att.check_out:
                # Try to find an open one as a fallback
                att = self.env['hr.attendance'].search([
                    ('employee_id', '=', line.employee_id.id),
                    ('check_out', '=', False),
                ], order='check_in desc', limit=1)

            if not att:
                raise UserError(_(
                    'No open attendance found for employee %s.', line.employee_id.name
                ))

            att.check_out = fields.Datetime.now()
            line.status = 'checked_out'
            line.attendance_id = att
        
        # Re-open the wizard to keep it open and refreshed
        wizard = self.mapped('wizard_id')
        if wizard:
            wizard._load_employee_lines()
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'manager.attendance.wizard',
                'res_id': wizard.id,
                'view_mode': 'form',
                'target': 'new',
            }
