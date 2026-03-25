# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ManagerTeamAccessRule(models.Model):
    _name = 'manager.team.access.rule'
    _description = 'Manager Team Access Rule'
    _order = 'sequence, model_id'

    name = fields.Char(string='Name', compute='_compute_name', store=True, readonly=True)
    sequence = fields.Integer(default=10)
    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
        ondelete='cascade',
        index=True,
        domain=[('transient', '=', False)],
    )
    model_name = fields.Char(related='model_id.model', string='Model Technical Name', readonly=True, store=True)
    employee_field = fields.Char(
        string='Employee Field',
        help='Field name linking to hr.employee. Use "id" for hr.employee itself. '
             'Leave empty for res.partner (work contacts of allowed employees).',
    )
    include_own = fields.Boolean(
        string='Include Own Records',
        default=True,
        help='Manager can see their own records (where employee = current user\'s employee).',
    )
    include_team = fields.Boolean(
        string='Include Team Records',
        default=True,
        help='Manager can see records of their direct and indirect subordinates.',
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.depends('model_id', 'employee_field')
    def _compute_name(self):
        for rec in self:
            if rec.model_id:
                if rec.employee_field:
                    field_info = ' / %s' % rec.employee_field
                elif rec.model_id.model == 'res.partner':
                    field_info = ' (work contacts)'
                else:
                    field_info = ''
                rec.name = '%s%s' % (rec.model_id.name, field_info)
            else:
                rec.name = ''

    @api.constrains('model_id', 'employee_field')
    def _check_employee_field(self):
        for rec in self:
            if not rec.model_id:
                continue
            # hr.employee uses field 'id'; res.partner uses work contacts (no field)
            if rec.model_id.model in ('hr.employee', 'res.partner'):
                continue
            if not rec.employee_field:
                raise ValidationError(
                    _('Employee field is required for model %s. Use "employee_id" for standard HR models.')
                    % rec.model_id.name
                )
            Model = self.env.get(rec.model_id.model)
            if Model and rec.employee_field not in Model._fields:
                raise ValidationError(
                    _('Model %s has no field "%s".') % (rec.model_id.model, rec.employee_field)
                )
