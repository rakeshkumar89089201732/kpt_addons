# -*- coding: utf-8 -*-

from odoo import api, fields, models


class HrSalaryAttachmentType(models.Model):
    _inherit = 'hr.salary.attachment.type'

    category = fields.Selection(
        selection=[
            ('deduction', 'Deduction'),
            ('allowance', 'Allowance'),
        ],
        string='Category',
        default='deduction',
        required=True,
        help='Deduction: Amount deducted from salary (e.g., loans, attachments).\n'
             'Allowance: Amount added to salary (e.g., tour expenses, reimbursements).'
    )

    # --- Odoo 17 custom note ---
    # The `show_in_mobile` feature is now maintained in `kpt_salary_attachment_approval`.
    # Kept here commented (not deleted) to avoid losing business logic/history.
    # show_in_mobile = fields.Boolean(
    #     string='Show in Mobile App',
    #     default=True,
    #     help='If enabled, this expense/attachment type will be visible and selectable in the KPT mobile application.',
    # )
    
    is_from_structure = fields.Boolean(
        string='From Salary Structure',
        compute='_compute_is_from_structure',
        store=True,
        help='True if this type was created from a salary structure rule'
    )
    
    @api.depends('code')
    def _compute_is_from_structure(self):
        """Check if this attachment type comes from a salary structure rule"""
        for rec in self:
            # Check if there's a salary rule with this code
            rule = self.env['hr.salary.rule'].search([
                ('code', '=', rec.code),
                ('active', '=', True)
            ], limit=1)
            rec.is_from_structure = bool(rule)
    
    def action_sync_from_structure(self):
        """Manually trigger sync of attachment types from salary structure rules"""
        self.env['hr.salary.rule']._sync_attachment_types_from_rules()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sync Completed',
                'message': 'Salary attachment types have been synced from salary structure rules.',
                'type': 'success',
                'sticky': False,
            }
        }
