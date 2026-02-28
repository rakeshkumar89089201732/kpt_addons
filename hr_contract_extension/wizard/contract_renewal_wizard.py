# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import timedelta


class ContractRenewalWizard(models.TransientModel):
    _name = 'contract.renewal.wizard'
    _description = 'Contract Renewal Confirmation Wizard'

    contract_id = fields.Many2one('hr.contract', string='Current Contract', required=True, readonly=True)
    employee_id = fields.Many2one('hr.employee', related='contract_id.employee_id', string='Employee', readonly=True)
    # Use Float to mirror hr.contract.gross type (avoid related monetary type mismatch)
    current_salary = fields.Float(related='contract_id.gross', string='Current Salary', readonly=True)
    currency_id = fields.Many2one('res.currency', related='contract_id.company_id.currency_id', readonly=True)
    warning_message = fields.Html(string='Warning', compute='_compute_warning_message')

    @api.depends('contract_id', 'employee_id')
    def _compute_warning_message(self):
        for wizard in self:
            if wizard.contract_id and wizard.employee_id:
                wizard.warning_message = f"""
                    <div style="padding: 12px; background-color: #fff9e6; border: 1px solid #f2c94c; border-radius: 6px; color: #5f4b00; max-width: 640px; line-height: 1.45;">
                        <p style="margin: 4px 0 10px 0; font-weight: 600; font-size: 14px;">Action</p>
                        <p style="margin: 2px 0;">
                            Expire current contract of <strong>{wizard.employee_id.name}</strong> and create a new <strong>Draft</strong> contract.
                        </p>
                        <p style="margin: 2px 0;">
                            You can edit the new draft (salary, dates, etc.) and then Start it. The old contract will remain closed.
                        </p>
                        <p style="margin: 8px 0 0 0; font-size: 12px; color: #6b5500;">
                            Note: Choose the correct start date on the new draft before starting it.
                        </p>
                    </div>
                """
            else:
                wizard.warning_message = ""

    def action_confirm_renewal(self):
        """Expire current contract and create new draft contract."""
        self.ensure_one()
        today = fields.Date.context_today(self)
        contract_start = self.contract_id.date_start
        # Close current contract effective today (or day before its own start if in future)
        end_date = today if not contract_start or contract_start <= today else contract_start - timedelta(days=1)
        self.contract_id.write({
            'state': 'close',
            'date_end': end_date,
        })
        
        # Create new draft contract
        new_contract = self.contract_id.copy({
            # Let user pick the new start date manually
            'date_start': False,
            'date_end': False,
            'state': 'draft',
            'name': self.contract_id._generate_contract_reference_from_employee(self.contract_id.employee_id),
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.contract',
            'res_id': new_contract.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_cancel(self):
        """Cancel the renewal process."""
        return {'type': 'ir.actions.act_window_close'}
