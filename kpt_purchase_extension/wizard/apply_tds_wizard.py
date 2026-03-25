from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ApplyTdsWizard(models.TransientModel):
    _name = 'apply.tds.wizard'
    _description = 'Apply TDS Taxes to Vendor Bill'

    move_id = fields.Many2one('account.move', string='Vendor Bill', required=True)
    tds_tax_ids = fields.Many2many(
        'account.tax',
        string='TDS Taxes',
        domain="[('type_tax_use', '=', 'purchase'), ('company_id', '=', company_id)]",
        help='Select TDS taxes to apply to this vendor bill'
    )
    company_id = fields.Many2one('res.company', related='move_id.company_id', store=True)
    
    def action_apply_tds(self):
        """Apply selected TDS taxes to the vendor bill"""
        self.ensure_one()
        
        if not self.tds_tax_ids:
            raise UserError(_('Please select at least one TDS tax to apply.'))
        
        if self.move_id.state != 'draft':
            raise UserError(_('You can only apply TDS taxes to draft bills.'))
        
        # Get the base amount for TDS calculation (sum of all product lines)
        base_amount = sum(
            line.price_subtotal 
            for line in self.move_id.invoice_line_ids 
            if line.display_type == 'product'
        )
        
        if not base_amount:
            raise UserError(_('No product lines found to calculate TDS on.'))
        
        # Create TDS tax lines
        for tax in self.tds_tax_ids:
            # Check if this TDS tax is already applied
            existing_tds_line = self.move_id.invoice_line_ids.filtered(
                lambda l: l.tax_line_id == tax and l.display_type == 'tax'
            )
            
            if existing_tds_line:
                continue  # Skip if already applied
            
            # Calculate TDS amount
            tax_result = tax.compute_all(
                base_amount,
                currency=self.move_id.currency_id,
                quantity=1,
                product=None,
                partner=self.move_id.partner_id
            )
            
            # Get tax amount (should be negative for TDS)
            tax_amount = 0
            for tax_line in tax_result['taxes']:
                if tax_line['id'] == tax.id:
                    tax_amount = tax_line['amount']
                    break
            
            # Get TDS account from tax repartition lines
            repartition_line = tax.invoice_repartition_line_ids.filtered(
                lambda l: l.repartition_type == 'tax'
            )[:1]
            
            if not repartition_line or not repartition_line.account_id:
                raise UserError(_(
                    'TDS tax "%s" does not have a tax account configured. '
                    'Please configure the tax account in the tax repartition lines.'
                ) % tax.name)
            
            # Create TDS tax line
            self.move_id.write({
                'invoice_line_ids': [(0, 0, {
                    'name': tax.name,
                    'account_id': repartition_line.account_id.id,
                    'quantity': 1,
                    'price_unit': tax_amount,
                    'tax_line_id': tax.id,
                    'tax_repartition_line_id': repartition_line.id,
                    'display_type': 'tax',
                    'sequence': 9999,  # Put at the end
                })]
            })
        
        # Recompute taxes and totals
        self.move_id._recompute_dynamic_lines(recompute_all_taxes=True)
        
        return {'type': 'ir.actions.act_window_close'}
