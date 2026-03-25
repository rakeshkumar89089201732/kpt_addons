# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PrintCopyWizard(models.TransientModel):
    _name = 'print.copy.wizard'
    _description = 'Print Copy Selection Wizard'

    num_copies = fields.Selection([
        ('1', 'Original'),
        ('2', 'Original + Duplicate'),
        ('3', 'Original + Duplicate + Triplicate'),
    ], string='Number of Copies', required=True, default='1')
    
    report_action_id = fields.Many2one('ir.actions.report', string='Report Action', required=True)
    record_ids = fields.Char(string='Record IDs')
    model_name = fields.Char(string='Model Name')

    def action_print_report(self):
        self.ensure_one()
        
        # Parse record IDs
        record_ids = eval(self.record_ids) if self.record_ids else []
        
        # Prepare context with copy information
        context = dict(self.env.context)
        context['num_copies'] = int(self.num_copies)
        
        # Generate the report
        return self.report_action_id.with_context(context).report_action(
            self.env[self.model_name].browse(record_ids)
        )
