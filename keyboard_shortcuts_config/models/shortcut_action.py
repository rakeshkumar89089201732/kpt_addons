# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ShortcutAction(models.Model):
    _name = 'shortcut.action'
    _description = 'Shortcut Action Definition'
    _order = 'sequence, name'

    name = fields.Char(string='Action Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    action_type = fields.Selection([
        ('navigation', 'Navigation'),
        ('form_action', 'Form Action'),
        ('text_input', 'Text Input'),
        ('record_action', 'Record Action'),
        ('custom_js', 'Custom JavaScript'),
    ], string='Action Type', required=True, default='navigation')
    
    action_code = fields.Char(string='Action Code', required=True,
                              help='Unique code for this action (e.g., next_field, save_record)')
    
    action_params = fields.Text(string='Action Parameters (JSON)',
                                help='JSON object with parameters for the action')
    
    description = fields.Text(string='Description', translate=True)
    
    active = fields.Boolean(string='Active', default=True)
    is_system = fields.Boolean(string='System Action', default=False,
                               help='System actions cannot be deleted')
    
    shortcut_count = fields.Integer(string='Shortcuts Using This', 
                                    compute='_compute_shortcut_count')
    
    @api.depends('action_code')
    def _compute_shortcut_count(self):
        for record in self:
            record.shortcut_count = self.env['keyboard.shortcut'].search_count([
                ('action_id', '=', record.id)
            ])
    
    @api.constrains('action_code')
    def _check_action_code_unique(self):
        for record in self:
            if self.search_count([
                ('action_code', '=', record.action_code),
                ('id', '!=', record.id)
            ]) > 0:
                raise ValidationError(_('Action code must be unique. "%s" already exists.') % record.action_code)
    
    def action_view_shortcuts(self):
        self.ensure_one()
        return {
            'name': _('Shortcuts Using This Action'),
            'type': 'ir.actions.act_window',
            'res_model': 'keyboard.shortcut',
            'view_mode': 'tree,form',
            'domain': [('action_id', '=', self.id)],
            'context': {'default_action_id': self.id},
        }
