# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.exceptions import UserError


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-create attachment types and input types for allowance rules"""
        rules = super().create(vals_list)
        self._sync_attachment_types_from_rules()
        return rules

    def write(self, vals):
        """Auto-sync attachment types when rules are updated"""
        result = super().write(vals)
        if 'code' in vals or 'category_id' in vals or 'active' in vals or 'condition_python' in vals:
            self._sync_attachment_types_from_rules()
        return result

    def unlink(self):
        """Clean up attachment types when rules are deleted"""
        result = super().unlink()
        self._sync_attachment_types_from_rules()
        return result

    @api.model
    def _sync_attachment_types_from_rules(self):
        """Automatically sync salary rules with attachment types and input types
        Creates attachment types for ALL allowance and deduction rules from salary structures
        (except BASIC and HRA), regardless of whether they currently use inputs.
        """
        # Get category references
        alw_category = self.env.ref('hr_payroll.ALW', raise_if_not_found=False)
        ded_category = self.env.ref('hr_payroll.DED', raise_if_not_found=False)
        
        if not alw_category or not ded_category:
            return
        
        # Get all active salary rules in ALW or DED categories
        # Exclude BASIC and HRA as they should not be available as salary attachments
        excluded_codes = ['BASIC', 'HRA']
        
        rules = self.env['hr.salary.rule'].search([
            ('active', '=', True),
            ('category_id', 'in', [alw_category.id, ded_category.id]),
        ])
        
        for rule in rules:
            if not rule.code:
                continue
            
            # Skip BASIC and HRA
            if rule.code in excluded_codes:
                continue
            
            # Determine category based on rule category
            category = 'deduction'  # default
            if rule.category_id:
                if rule.category_id.code == 'ALW':
                    category = 'allowance'
                elif rule.category_id.code == 'DED':
                    category = 'deduction'
            
            # Create or update attachment type
            attachment_type = self.env['hr.salary.attachment.type'].search([
                ('code', '=', rule.code)
            ], limit=1)
            
            if not attachment_type:
                self.env['hr.salary.attachment.type'].create({
                    'name': rule.name,
                    'code': rule.code,
                    'category': category,
                    'is_from_structure': True,
                })
            else:
                # Update name and category if changed
                if attachment_type.name != rule.name or attachment_type.category != category:
                    attachment_type.write({
                        'name': rule.name,
                        'category': category,
                        'is_from_structure': True,
                    })
                elif not attachment_type.is_from_structure:
                    attachment_type.write({'is_from_structure': True})
            
            # Create or update input type
            input_type = self.env['hr.payslip.input.type'].search([
                ('code', '=', rule.code)
            ], limit=1)
            
            if not input_type:
                self.env['hr.payslip.input.type'].create({
                    'name': rule.name,
                    'code': rule.code,
                })
            elif input_type.name != rule.name:
                input_type.write({'name': rule.name})
            
            # Ensure the rule can handle inputs - modify rule to check inputs first
            self._ensure_rule_uses_inputs(rule)
    
    @api.model
    def _ensure_rule_uses_inputs(self, rule):
        """Ensure a salary rule can handle inputs from salary attachments.
        If the rule doesn't already use inputs, modify it to check inputs first, then fall back to original logic.
        """
        if not rule.code or rule.condition_select != 'python':
            return

        condition = rule.condition_python or ''
        amount_code = rule.amount_python_compute or ''
        
        # Check if rule already uses inputs correctly
        if 'inputs' in condition and (f"'{rule.code}'" in condition or f'"{rule.code}"' in condition):
            # Also check if amount_code is valid (not corrupted)
            if amount_code and 'inputs' in amount_code and rule.code in amount_code:
                return  # Rule already handles inputs correctly
            # If condition is correct but amount is corrupted, we'll fix it below
        
        # Modify condition to check inputs first
        # Pattern: result = 'CODE' in inputs or (original condition)
        if 'inputs' not in condition or rule.code not in condition:
            # Add input check to condition
            original_condition = condition.strip()
            if not original_condition:
                original_condition = 'True'  # Default condition
            
            if original_condition.startswith('result ='):
                condition_part = original_condition.replace('result =', '').strip()
                new_condition = f"result = '{rule.code}' in inputs or ({condition_part})"
            else:
                new_condition = f"result = '{rule.code}' in inputs or ({original_condition})"
            
            # Only update if condition actually changed
            if new_condition != condition:
                rule.write({'condition_python': new_condition})
        
        # -----------------------------
        # Modify amount to use inputs if available
        # -----------------------------
        # First check if rule is already corrupted (has invalid syntax)
        is_corrupted = False
        if amount_code and ('(result =' in amount_code or '(result=' in amount_code):
            # Rule was corrupted - try to extract the original expression
            is_corrupted = True
            # Try to find the original expression by looking for patterns
            # This is a fallback - ideally we'd restore from XML but that's complex
            import re
            # Look for pattern like: or (result = ...)
            match = re.search(r'or\s*\(result\s*=\s*(.+?)\)\s*$', amount_code, re.DOTALL)
            if match:
                expression = match.group(1).strip()
            else:
                # Can't extract, skip modification
                return
        
        if 'inputs' not in amount_code or rule.code not in amount_code or is_corrupted:
            # Get the original amount computation (for python-code rules)
            original_amount = (amount_code or '').strip()

            # If this rule was not a python-code amount originally (amount_select != 'code'),
            # there may be no meaningful python expression to reuse. In that case we make
            # the rule fully driven by inputs and use 0.0 as fallback.
            if rule.amount_select != 'code':
                original_amount = original_amount or '0.0'
                # Switch the rule to python-code computation so amount_python_compute is used
                rule.write({'amount_select': 'code'})
            elif not original_amount:
                original_amount = '0.0'  # Default amount
            
            # Extract the expression part (remove 'result =' if present)
            if is_corrupted:
                # Expression already extracted above
                pass
            elif original_amount.startswith('result ='):
                expression = original_amount.replace('result =', '').strip()
            elif original_amount.startswith('result='):
                expression = original_amount.replace('result=', '').strip()
            else:
                expression = original_amount
            
            # Ensure expression doesn't contain 'result =' (shouldn't happen but safety check)
            if 'result =' in expression or 'result=' in expression:
                # Try to extract just the right side
                if 'result =' in expression:
                    expression = expression.split('result =', 1)[-1].strip()
                elif 'result=' in expression:
                    expression = expression.split('result=', 1)[-1].strip()
            
            # Create new amount that checks inputs first
            if rule.category_id and rule.category_id.code == 'ALW':
                # Allowance: positive amount
                new_amount = f"""result = inputs.get('{rule.code}', False) and inputs['{rule.code}'].amount or ({expression})
result_name = inputs.get('{rule.code}', False) and inputs['{rule.code}'].name or ''"""
            else:
                # Deduction: negative amount (if from inputs)
                # For deductions, if input exists use it, otherwise use original
                new_amount = f"""result = inputs.get('{rule.code}', False) and -inputs['{rule.code}'].amount or ({expression})
result_name = inputs.get('{rule.code}', False) and inputs['{rule.code}'].name or ''"""
            
            # Only update if amount actually changed
            if new_amount != amount_code:
                rule.write({'amount_python_compute': new_amount})
    
    def action_fix_pf_rule(self):
        """Fix the PF rule if it was corrupted"""
        pf_rule = self.search([('code', '=', 'PF')], limit=1)
        if pf_rule:
            # Restore original PF rule definition
            pf_rule.write({
                'condition_python': 'result = bool(contract and contract.apply_pf and contract.deduct_employee_pf_in_net_pay and (contract.employee_provident_fund or 0.0))',
                'amount_python_compute': 'result = -(contract.employee_provident_fund or 0.0)',
            })
            # Now apply the correct modification
            self._ensure_rule_uses_inputs(pf_rule)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'PF Rule Fixed',
                    'message': 'The PF rule has been restored and updated correctly.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'PF Rule Not Found',
                'message': 'Could not find the PF rule.',
                'type': 'warning',
                'sticky': False,
            }
        }


def post_init_hook(env):
    """Sync attachment types from existing salary rules after module installation.
    Odoo 17 calls post_init_hook with a single argument: env."""
    env['hr.salary.rule']._sync_attachment_types_from_rules()
