# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import AccessError, ValidationError
import json


class KeyboardShortcut(models.Model):
    _name = 'keyboard.shortcut'
    _description = 'Keyboard Shortcut Configuration'
    _order = 'sequence, id'

    name = fields.Char(string='Shortcut Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Shortcut Key Configuration
    key_code = fields.Char(string='Key Code', required=True, help='The main key code (e.g., Enter, Tab, S)')
    ctrl_key = fields.Boolean(string='Ctrl', default=False)
    alt_key = fields.Boolean(string='Alt', default=False)
    shift_key = fields.Boolean(string='Shift', default=False)
    meta_key = fields.Boolean(string='Meta/Cmd', default=False)
    
    # Display field for the complete shortcut
    shortcut_display = fields.Char(string='Shortcut', compute='_compute_shortcut_display', store=True)
    
    # Action Configuration
    action_id = fields.Many2one('shortcut.action', string='Action', required=True, ondelete='cascade')
    action_type = fields.Selection(related='action_id.action_type', string='Action Type', store=True)
    
    # Scope Configuration
    scope = fields.Selection([
        ('global', 'Global (All Users)'),
        ('user', 'User Specific'),
    ], string='Scope', required=True, default='user')
    
    user_id = fields.Many2one('res.users', string='User', 
                              help='Leave empty for global shortcuts')
    
    # Context Configuration
    apply_on_view = fields.Selection([
        ('all', 'All Views'),
        ('form', 'Form View'),
        ('list', 'List View'),
        ('kanban', 'Kanban View'),
        ('calendar', 'Calendar View'),
        ('pivot', 'Pivot View'),
        ('graph', 'Graph View'),
    ], string='Apply On', default='all', required=True)
    
    model_ids = fields.Many2many('ir.model', string='Specific Models',
                                 help='Leave empty to apply on all models')
    
    # Status
    active = fields.Boolean(string='Active', default=True)
    is_system = fields.Boolean(string='System Shortcut', default=False,
                               help='System shortcuts cannot be deleted')
    
    # Additional Configuration
    description = fields.Text(string='Description', translate=True)
    prevent_default = fields.Boolean(string='Prevent Default Action', default=True,
                                     help='Prevent the browser default action for this key')
    stop_propagation = fields.Boolean(string='Stop Propagation', default=False,
                                      help='Stop the event from bubbling up')
    
    # Conflict Detection
    conflict_ids = fields.Many2many('keyboard.shortcut', 'shortcut_conflict_rel',
                                    'shortcut_id', 'conflict_id',
                                    string='Conflicting Shortcuts',
                                    compute='_compute_conflicts', store=True)
    has_conflicts = fields.Boolean(string='Has Conflicts', compute='_compute_conflicts', store=True)
    conflict_count = fields.Integer(string='Conflict Count', compute='_compute_conflicts', store=True)
    
    @api.depends('key_code', 'ctrl_key', 'alt_key', 'shift_key', 'meta_key')
    def _compute_shortcut_display(self):
        for record in self:
            parts = []
            if record.ctrl_key:
                parts.append('Ctrl')
            if record.alt_key:
                parts.append('Alt')
            if record.shift_key:
                parts.append('Shift')
            if record.meta_key:
                parts.append('Meta')
            if record.key_code:
                parts.append(record.key_code)
            record.shortcut_display = ' + '.join(parts) if parts else ''
    
    @api.depends('key_code', 'ctrl_key', 'alt_key', 'shift_key', 'meta_key', 
                 'scope', 'user_id', 'apply_on_view', 'model_ids', 'active')
    def _compute_conflicts(self):
        for record in self:
            if not record.active:
                record.conflict_ids = [(5, 0, 0)]
                record.has_conflicts = False
                record.conflict_count = 0
                continue

            record_id = record._origin.id or False
            domain = [
                ('key_code', '=', record.key_code),
                ('ctrl_key', '=', record.ctrl_key),
                ('alt_key', '=', record.alt_key),
                ('shift_key', '=', record.shift_key),
                ('meta_key', '=', record.meta_key),
                ('active', '=', True),
            ]

            # During onchange on a new record, record.id is a temporary NewId
            # placeholder that cannot be used in SQL domains.
            if record_id:
                domain.insert(0, ('id', '!=', record_id))
            
            # Check scope conflicts
            if record.scope == 'global':
                domain.append(('scope', '=', 'global'))
            else:
                domain.append('|')
                domain.append(('scope', '=', 'global'))
                domain.append(('user_id', '=', record.user_id.id))
            
            conflicts = self.search(domain)
            
            # Filter by view and model context
            filtered_conflicts = self.env['keyboard.shortcut']
            for conflict in conflicts:
                if self._has_context_overlap(record, conflict):
                    filtered_conflicts |= conflict
            
            record.conflict_ids = [(6, 0, filtered_conflicts.ids)]
            record.has_conflicts = bool(filtered_conflicts)
            record.conflict_count = len(filtered_conflicts)
    
    def _has_context_overlap(self, shortcut1, shortcut2):
        """Check if two shortcuts have overlapping contexts"""
        # Check view overlap
        if shortcut1.apply_on_view != 'all' and shortcut2.apply_on_view != 'all':
            if shortcut1.apply_on_view != shortcut2.apply_on_view:
                return False
        
        # Check model overlap
        if shortcut1.model_ids and shortcut2.model_ids:
            common_models = shortcut1.model_ids & shortcut2.model_ids
            if not common_models:
                return False
        
        return True
    
    @api.constrains('scope', 'user_id')
    def _check_user_scope(self):
        for record in self:
            if record.scope == 'user' and not record.user_id:
                raise ValidationError(_('User specific shortcuts must have a user assigned.'))
            if record.scope == 'global' and record.user_id:
                raise ValidationError(_('Global shortcuts cannot have a specific user assigned.'))
    
    @api.constrains('key_code')
    def _check_key_code(self):
        for record in self:
            if not record.key_code or len(record.key_code.strip()) == 0:
                raise ValidationError(_('Key code cannot be empty.'))
    
    def action_view_conflicts(self):
        self.ensure_one()
        return {
            'name': _('Conflicting Shortcuts'),
            'type': 'ir.actions.act_window',
            'res_model': 'keyboard.shortcut',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.conflict_ids.ids)],
            'context': {'create': False},
        }
    
    def get_shortcuts_for_user(self, user_id=None):
        """Get all active shortcuts for a specific user"""
        if user_id is None:
            user_id = self.env.user.id

        # The frontend service loads on every backend session. If a user does
        # not effectively inherit the shortcut groups yet, fail closed instead
        # of raising an access error on login/navigation.
        if not (
            self.env.user.has_group('keyboard_shortcuts_config.group_shortcut_user')
            or self.env.user.has_group('keyboard_shortcuts_config.group_shortcut_manager')
        ):
            return []
        
        domain = [
            ('active', '=', True),
            '|',
            ('scope', '=', 'global'),
            ('user_id', '=', user_id),
        ]

        try:
            shortcuts = self.search(domain)
        except AccessError:
            return []
        
        result = []
        for shortcut in shortcuts:
            result.append({
                'id': shortcut.id,
                'name': shortcut.name,
                'key_code': shortcut.key_code,
                'ctrl_key': shortcut.ctrl_key,
                'alt_key': shortcut.alt_key,
                'shift_key': shortcut.shift_key,
                'meta_key': shortcut.meta_key,
                'action_type': shortcut.action_type,
                'action_code': shortcut.action_id.action_code,
                'action_params': json.loads(shortcut.action_id.action_params or '{}'),
                'apply_on_view': shortcut.apply_on_view,
                'model_ids': shortcut.model_ids.mapped('model'),
                'prevent_default': shortcut.prevent_default,
                'stop_propagation': shortcut.stop_propagation,
                'scope': shortcut.scope,
            })
        
        return result
    
    @api.model
    def get_user_shortcuts_json(self):
        """API method to get shortcuts as JSON for JavaScript"""
        return self.get_shortcuts_for_user()
    
    def action_duplicate_for_user(self):
        """Duplicate a global shortcut for current user"""
        self.ensure_one()
        if self.scope != 'global':
            raise ValidationError(_('Only global shortcuts can be duplicated for users.'))
        
        return self.copy({
            'name': f"{self.name} (My Copy)",
            'scope': 'user',
            'user_id': self.env.user.id,
            'is_system': False,
        })
    
    def action_test_shortcut(self):
        """Test action for the shortcut"""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Shortcut Test'),
                'message': _('Shortcut "%s" would trigger action: %s') % (
                    self.shortcut_display, self.action_id.name
                ),
                'type': 'info',
                'sticky': False,
            }
        }
