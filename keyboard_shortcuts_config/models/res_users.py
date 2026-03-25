# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    shortcut_ids = fields.One2many('keyboard.shortcut', 'user_id', 
                                   string='Personal Shortcuts')
    shortcut_count = fields.Integer(string='Shortcuts', compute='_compute_shortcut_count')
    
    enable_shortcuts = fields.Boolean(string='Enable Keyboard Shortcuts', default=True,
                                     help='Enable/disable all keyboard shortcuts for this user')
    
    @api.depends('shortcut_ids')
    def _compute_shortcut_count(self):
        for user in self:
            user.shortcut_count = len(user.shortcut_ids)
    
    def action_view_shortcuts(self):
        self.ensure_one()
        return {
            'name': 'My Keyboard Shortcuts',
            'type': 'ir.actions.act_window',
            'res_model': 'keyboard.shortcut',
            'view_mode': 'tree,form',
            'domain': [
                '|',
                ('user_id', '=', self.id),
                ('scope', '=', 'global'),
            ],
            'context': {
                'default_user_id': self.id,
                'default_scope': 'user',
            },
        }
    
    def action_reset_shortcuts(self):
        """Reset user shortcuts to system defaults"""
        self.ensure_one()
        self.shortcut_ids.filtered(lambda s: not s.is_system).unlink()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Shortcuts Reset',
                'message': 'Your personal shortcuts have been reset to defaults.',
                'type': 'success',
                'sticky': False,
            }
        }
