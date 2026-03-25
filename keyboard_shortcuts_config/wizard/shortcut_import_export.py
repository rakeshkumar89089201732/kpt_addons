# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
import base64


class ShortcutImportExport(models.TransientModel):
    _name = 'shortcut.import.export'
    _description = 'Import/Export Keyboard Shortcuts'

    operation = fields.Selection([
        ('export', 'Export'),
        ('import', 'Import'),
    ], string='Operation', required=True, default='export')
    
    export_scope = fields.Selection([
        ('my', 'My Shortcuts Only'),
        ('global', 'Global Shortcuts Only'),
        ('all', 'All Shortcuts'),
    ], string='Export Scope', default='my')
    
    import_file = fields.Binary(string='Import File', attachment=False)
    import_filename = fields.Char(string='Filename')
    
    export_file = fields.Binary(string='Export File', readonly=True, attachment=False)
    export_filename = fields.Char(string='Export Filename', readonly=True)
    
    import_mode = fields.Selection([
        ('add', 'Add to Existing'),
        ('replace', 'Replace All'),
    ], string='Import Mode', default='add')
    
    @api.onchange('operation')
    def _onchange_operation(self):
        if self.operation == 'export':
            self.import_file = False
            self.import_filename = False
    
    def action_export(self):
        self.ensure_one()
        
        domain = [('active', '=', True)]
        
        if self.export_scope == 'my':
            domain.append(('user_id', '=', self.env.user.id))
        elif self.export_scope == 'global':
            domain.append(('scope', '=', 'global'))
        
        shortcuts = self.env['keyboard.shortcut'].search(domain)
        
        if not shortcuts:
            raise UserError(_('No shortcuts found to export.'))
        
        export_data = []
        for shortcut in shortcuts:
            export_data.append({
                'name': shortcut.name,
                'key_code': shortcut.key_code,
                'ctrl_key': shortcut.ctrl_key,
                'alt_key': shortcut.alt_key,
                'shift_key': shortcut.shift_key,
                'meta_key': shortcut.meta_key,
                'action_code': shortcut.action_id.action_code,
                'scope': shortcut.scope,
                'apply_on_view': shortcut.apply_on_view,
                'model_ids': shortcut.model_ids.mapped('model'),
                'prevent_default': shortcut.prevent_default,
                'stop_propagation': shortcut.stop_propagation,
                'description': shortcut.description or '',
            })
        
        json_data = json.dumps(export_data, indent=2)
        self.export_file = base64.b64encode(json_data.encode('utf-8'))
        self.export_filename = f'keyboard_shortcuts_{self.export_scope}.json'
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'shortcut.import.export',
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
    
    def action_import(self):
        self.ensure_one()
        
        if not self.import_file:
            raise UserError(_('Please select a file to import.'))
        
        try:
            json_data = base64.b64decode(self.import_file).decode('utf-8')
            import_data = json.loads(json_data)
        except Exception as e:
            raise UserError(_('Invalid file format. Please provide a valid JSON file.\nError: %s') % str(e))
        
        if not isinstance(import_data, list):
            raise UserError(_('Invalid file structure. Expected a list of shortcuts.'))
        
        if self.import_mode == 'replace':
            domain = [('user_id', '=', self.env.user.id), ('is_system', '=', False)]
            self.env['keyboard.shortcut'].search(domain).unlink()
        
        imported_count = 0
        errors = []
        
        for idx, shortcut_data in enumerate(import_data):
            try:
                action = self.env['shortcut.action'].search([
                    ('action_code', '=', shortcut_data.get('action_code'))
                ], limit=1)
                
                if not action:
                    errors.append(f"Line {idx + 1}: Action '{shortcut_data.get('action_code')}' not found")
                    continue
                
                model_ids = []
                if shortcut_data.get('model_ids'):
                    for model_name in shortcut_data['model_ids']:
                        model = self.env['ir.model'].search([('model', '=', model_name)], limit=1)
                        if model:
                            model_ids.append(model.id)
                
                vals = {
                    'name': shortcut_data.get('name'),
                    'key_code': shortcut_data.get('key_code'),
                    'ctrl_key': shortcut_data.get('ctrl_key', False),
                    'alt_key': shortcut_data.get('alt_key', False),
                    'shift_key': shortcut_data.get('shift_key', False),
                    'meta_key': shortcut_data.get('meta_key', False),
                    'action_id': action.id,
                    'scope': 'user',
                    'user_id': self.env.user.id,
                    'apply_on_view': shortcut_data.get('apply_on_view', 'all'),
                    'model_ids': [(6, 0, model_ids)],
                    'prevent_default': shortcut_data.get('prevent_default', True),
                    'stop_propagation': shortcut_data.get('stop_propagation', False),
                    'description': shortcut_data.get('description', ''),
                }
                
                self.env['keyboard.shortcut'].create(vals)
                imported_count += 1
                
            except Exception as e:
                errors.append(f"Line {idx + 1}: {str(e)}")
        
        message = _('%d shortcuts imported successfully.') % imported_count
        if errors:
            message += '\n\nErrors:\n' + '\n'.join(errors)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import Complete'),
                'message': message,
                'type': 'success' if not errors else 'warning',
                'sticky': True,
            }
        }
