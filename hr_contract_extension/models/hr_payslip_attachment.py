# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.fields import Command


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    @api.depends('employee_id', 'contract_id', 'struct_id', 'date_from', 'date_to', 'struct_id')
    def _compute_input_line_ids(self):
        """Override to handle both deductions and allowances"""
        attachment_types = self._get_attachment_types()
        attachment_type_ids = [f.id for f in attachment_types.values()]
        
        for slip in self:
            if not slip.employee_id or not slip.employee_id.salary_attachment_ids or not slip.struct_id:
                lines_to_remove = slip.input_line_ids.filtered(
                    lambda x: x.input_type_id.id in attachment_type_ids
                )
                slip.update({'input_line_ids': [Command.unlink(line.id) for line in lines_to_remove]})
                continue
                
            if slip.employee_id.salary_attachment_ids and slip.date_to:
                lines_to_remove = slip.input_line_ids.filtered(
                    lambda x: x.input_type_id.id in attachment_type_ids
                )
                input_line_vals = [Command.unlink(line.id) for line in lines_to_remove]

                valid_attachments = slip.employee_id.salary_attachment_ids.filtered(
                    lambda a: a.state == 'open'
                        and a.date_start <= slip.date_to
                        and (not a.date_end or a.date_end >= slip.date_from)
                )
                
                # Get all attachment types (both deduction and allowance) present in structure
                attachment_type_codes = list(set(valid_attachments.deduction_type_id.mapped('code')))
                struct_rule_codes = list(set(slip.struct_id.rule_ids.mapped('code')))
                included_types = [
                    code for code in attachment_type_codes 
                    if attachment_types[code].code in struct_rule_codes
                ]
                
                # Generate input lines for all included types
                for attachment_type_code in included_types:
                    if not slip.struct_id.rule_ids.filtered(
                        lambda r: r.active and r.code == attachment_types[attachment_type_code].code
                    ):
                        continue
                    
                    attachments = valid_attachments.filtered(
                        lambda a: a.deduction_type_id.code == attachment_type_code
                    )
                    if not attachments:
                        continue
                        
                    amount = attachments._get_active_amount()
                    name = ', '.join(attachments.mapped('description'))
                    input_type_id = attachment_types[attachment_type_code].id
                    
                    # Get the actual attachment type to check category
                    salary_attachment_type = self.env['hr.salary.attachment.type'].search([
                        ('code', '=', attachment_type_code)
                    ], limit=1)
                    
                    # For both allowances and deductions, store a POSITIVE amount in the input line.
                    # The salary rule (amount_python_compute) is responsible for applying + or - sign.
                    # For credit notes, invert the amount.
                    final_amount = amount if not slip.credit_note else -amount
                    
                    input_line_vals.append(Command.create({
                        'name': name,
                        'amount': final_amount,
                        'input_type_id': input_type_id,
                    }))
                
                slip.update({'input_line_ids': input_line_vals})
