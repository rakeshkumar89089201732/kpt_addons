from odoo import models, fields, api
from odoo.exceptions import UserError


class TDSRegimeComparisonWizard(models.TransientModel):
    _name = 'tds.regime.comparison.wizard'
    _description = 'TDS Regime Comparison Wizard'
    
    hr_tds_id = fields.Many2one('hr.tds', 'TDS Record', required=True, readonly=True)
    
    # Old Regime Fields
    old_annual_salary = fields.Float('Annual Salary', readonly=True)
    old_total_exemptions = fields.Float('Total Exemptions', readonly=True)
    old_total_deductions = fields.Float('Total Deductions', readonly=True)
    old_taxable_amount = fields.Float('Taxable Income', readonly=True)
    old_tax_payable = fields.Float('Tax Payable', readonly=True)
    old_deduction_breakdown = fields.Html('Deduction Breakdown', readonly=True)
    old_regime_slab_id = fields.Many2one('tax.slab', 'Old Regime Slab', readonly=True)
    
    # New Regime Fields
    new_annual_salary = fields.Float('Annual Salary', readonly=True)
    new_total_exemptions = fields.Float('Total Exemptions', readonly=True)
    new_total_deductions = fields.Float('Total Deductions', readonly=True)
    new_taxable_amount = fields.Float('Taxable Income', readonly=True)
    new_tax_payable = fields.Float('Tax Payable', readonly=True)
    new_deduction_breakdown = fields.Html('Deduction Breakdown', readonly=True)
    new_regime_slab_id = fields.Many2one('tax.slab', 'New Regime Slab', readonly=True)
    
    # Comparison Fields
    recommended_regime = fields.Selection([
        ('old', 'Old Tax Regime'),
        ('new', 'New Tax Regime'),
    ], string='Recommended Regime', readonly=True)
    tax_difference = fields.Float('Tax Difference', readonly=True, help='Absolute difference in tax liability')
    comparison_summary = fields.Html('Comparison Summary', readonly=True)
    
    # Current regime for highlighting
    current_regime = fields.Selection([
        ('old', 'Old Tax Regime'),
        ('new', 'New Tax Regime'),
    ], string='Current Regime', readonly=True)
    
    @api.model
    def default_get(self, fields_list):
        """Populate comparison data from TDS record"""
        res = super().default_get(fields_list)
        
        # Get TDS record from context
        tds_id = self.env.context.get('default_hr_tds_id') or self.env.context.get('active_id')
        if not tds_id:
            raise UserError('No TDS record found. Please open this wizard from a TDS record.')
        
        tds = self.env['hr.tds'].browse(tds_id)
        if not tds.exists():
            raise UserError('TDS record not found.')
        
        res['hr_tds_id'] = tds.id
        res['current_regime'] = tds.tax_regime_type or 'old'
        
        # Get tax slabs for both regimes - more flexible matching based on FY overlap
        fy_start = tds.tds_from_date
        fy_end = tds.tds_to_date
        
        # Search for slabs covering this FY (slabs where FY overlaps with slab period)
        old_slab = self.env['tax.slab'].search([
            ('tax_regime_type', '=', 'old'),
            ('date_start', '<=', fy_end),  # Slab starts before or during FY
            ('date_end', '>=', fy_start),  # Slab ends after or during FY
            ('active', '=', True),
        ], order='date_start desc', limit=1)  # Get most recent if multiple
        
        new_slab = self.env['tax.slab'].search([
            ('tax_regime_type', '=', 'new'),
            ('date_start', '<=', fy_end),
            ('date_end', '>=', fy_start),
            ('active', '=', True),
        ], order='date_start desc', limit=1)
        
        if not old_slab or not new_slab:
            # Build helpful error message
            error_msg = 'Tax slabs not found for the financial year. '
            if not old_slab:
                error_msg += 'Missing: Old Tax Regime slab. '
            if not new_slab:
                error_msg += 'Missing: New Tax Regime slab. '
            error_msg += f'Please configure tax slabs that cover the period {fy_start} to {fy_end}.'
            raise UserError(error_msg)
        
        res['old_regime_slab_id'] = old_slab.id
        res['new_regime_slab_id'] = new_slab.id
        
        # Calculate for Old Regime
        old_calc = self._calculate_regime_tax(tds, 'old', old_slab)
        res['old_annual_salary'] = old_calc['annual_salary']
        res['old_total_exemptions'] = old_calc['total_exemptions']
        res['old_total_deductions'] = old_calc['total_deductions']
        res['old_taxable_amount'] = old_calc['taxable_amount']
        res['old_tax_payable'] = old_calc['tax_payable']
        res['old_deduction_breakdown'] = old_calc['deduction_breakdown']
        
        # Calculate for New Regime
        new_calc = self._calculate_regime_tax(tds, 'new', new_slab)
        res['new_annual_salary'] = new_calc['annual_salary']
        res['new_total_exemptions'] = new_calc['total_exemptions']
        res['new_total_deductions'] = new_calc['total_deductions']
        res['new_taxable_amount'] = new_calc['taxable_amount']
        res['new_tax_payable'] = new_calc['tax_payable']
        res['new_deduction_breakdown'] = new_calc['deduction_breakdown']
        
        # Determine recommendation
        if old_calc['tax_payable'] < new_calc['tax_payable']:
            res['recommended_regime'] = 'old'
            res['tax_difference'] = new_calc['tax_payable'] - old_calc['tax_payable']
        else:
            res['recommended_regime'] = 'new'
            res['tax_difference'] = old_calc['tax_payable'] - new_calc['tax_payable']
        
        # Generate comparison summary
        res['comparison_summary'] = self._generate_comparison_summary(
            old_calc, new_calc, res['recommended_regime'], res['tax_difference']
        )
        
        return res
    
    def _calculate_regime_tax(self, tds, regime_type, tax_slab):
        """Calculate tax for a specific regime"""
        
        # Base salary (same for both)
        annual_salary = tds.annual_salary or 0.0
        previous_employer = tds.previous_employer_taxable or 0.0
        perquisites = tds.perquisites_17_2 or 0.0
        profits = tds.profits_17_3 or 0.0
        other_income = tds.total_other_income or 0.0
        
        gross_income = annual_salary + previous_employer + perquisites + profits + other_income
        
        # Get deductions for this regime
        deductions = self.env['deduction.description'].search([
            ('hr_tds_id', '=', tds.id),
            ('tax_regime_type', '=', regime_type),
        ])
        
        total_deductions = sum(deductions.mapped('deduction_amt'))
        
        # Exemptions (only for old regime)
        if regime_type == 'old':
            total_exemptions = (tds.total_exemptions_10 or 0.0) + (tds.total_hra_exemption or 0.0)
        else:
            total_exemptions = 0.0
        
        # Standard deduction (allowed in both, but different amounts)
        standard_deduction = tds.standard_deduction_16_ii or 0.0
        
        # Calculate taxable income
        taxable_income = gross_income - total_exemptions - total_deductions - standard_deduction
        taxable_income = max(taxable_income, 0.0)
        
        # Calculate tax based on slab
        tax_payable = self._calculate_tax_from_slab(taxable_income, tax_slab)
        
        # Add cess
        cess = tax_payable * 0.04
        total_tax = tax_payable + cess
        
        # Generate deduction breakdown HTML
        deduction_breakdown = self._generate_deduction_breakdown(deductions, total_exemptions, standard_deduction, regime_type)
        
        return {
            'annual_salary': gross_income,
            'total_exemptions': total_exemptions,
            'total_deductions': total_deductions + standard_deduction,
            'taxable_amount': taxable_income,
            'tax_payable': total_tax,
            'deduction_breakdown': deduction_breakdown,
        }
    
    def _calculate_tax_from_slab(self, taxable_income, tax_slab):
        """Calculate tax based on slab rates"""
        tax = 0.0
        
        for slab_line in tax_slab.tax_regime_line_ids.sorted(key=lambda x: x.tax_regime_amt_from):
            slab_from = slab_line.tax_regime_amt_from
            slab_to = slab_line.tax_regime_amt_to
            slab_rate = slab_line.tax_regime_per / 100.0
            
            if taxable_income <= slab_from:
                break
            
            if slab_to == 0:  # Unlimited upper limit
                taxable_in_slab = taxable_income - slab_from
            else:
                taxable_in_slab = min(taxable_income, slab_to) - slab_from
            
            if taxable_in_slab > 0:
                tax += taxable_in_slab * slab_rate
        
        # Apply rebate if applicable
        if tax_slab.enable_rebate_87a:
            if taxable_income <= tax_slab.rebate_87a_income_limit:
                tax = max(0.0, tax - tax_slab.rebate_87a_amount)
        
        return tax
    
    def _generate_deduction_breakdown(self, deductions, exemptions, standard_deduction, regime_type):
        """Generate HTML breakdown of deductions"""
        html = '<table class="table table-sm">'
        html += '<thead><tr><th>Section/Scheme</th><th class="text-right">Amount</th></tr></thead>'
        html += '<tbody>'
        
        if standard_deduction > 0:
            html += f'<tr><td>Standard Deduction u/s 16(ii)</td><td class="text-right">₹ {standard_deduction:,.0f}</td></tr>'
        
        if exemptions > 0 and regime_type == 'old':
            html += f'<tr><td>Section 10 Exemptions (HRA, etc.)</td><td class="text-right">₹ {exemptions:,.0f}</td></tr>'
        
        # Group deductions by section
        sections = {}
        for ded in deductions:
            section_name = ded.section_id.name if ded.section_id else 'Other'
            if section_name not in sections:
                sections[section_name] = []
            sections[section_name].append(ded)
        
        for section_name, ded_list in sections.items():
            section_total = sum(d.deduction_amt for d in ded_list)
            html += f'<tr><td><strong>{section_name}</strong></td><td class="text-right"><strong>₹ {section_total:,.0f}</strong></td></tr>'
            for ded in ded_list:
                scheme_name = (ded.scheme_id.display_name or ded.scheme_id.scheme_name) if ded.scheme_id else ded.name
                html += f'<tr><td>&nbsp;&nbsp;↳ {scheme_name}</td><td class="text-right">₹ {ded.deduction_amt:,.0f}</td></tr>'
        
        if not deductions and exemptions == 0 and standard_deduction == 0:
            html += '<tr><td colspan="2" class="text-center text-muted">No deductions claimed</td></tr>'
        
        html += '</tbody></table>'
        return html
    
    def _generate_comparison_summary(self, old_calc, new_calc, recommended, difference):
        """Generate comparison summary HTML"""
        html = '<div class="alert alert-'
        html += 'success' if recommended == 'new' else 'info'
        html += '" role="alert">'
        html += '<h4 class="alert-heading">💡 Recommendation</h4>'
        
        if recommended == 'old':
            html += f'<p><strong>Old Tax Regime</strong> is recommended for you.</p>'
            html += f'<p>You will save <strong>₹ {difference:,.0f}</strong> annually by choosing the Old Regime.</p>'
            html += '<ul>'
            html += f'<li>Old Regime Tax: ₹ {old_calc["tax_payable"]:,.0f}</li>'
            html += f'<li>New Regime Tax: ₹ {new_calc["tax_payable"]:,.0f}</li>'
            html += f'<li>Your deductions (₹ {old_calc["total_deductions"]:,.0f}) and exemptions (₹ {old_calc["total_exemptions"]:,.0f}) provide significant tax savings.</li>'
            html += '</ul>'
        else:
            html += f'<p><strong>New Tax Regime</strong> is recommended for you.</p>'
            html += f'<p>You will save <strong>₹ {difference:,.0f}</strong> annually by choosing the New Regime.</p>'
            html += '<ul>'
            html += f'<li>New Regime Tax: ₹ {new_calc["tax_payable"]:,.0f}</li>'
            html += f'<li>Old Regime Tax: ₹ {old_calc["tax_payable"]:,.0f}</li>'
            html += '<li>The lower slab rates in New Regime outweigh the deduction benefits of Old Regime.</li>'
            html += '</ul>'
        
        html += '</div>'
        return html
    
    def action_select_old_regime(self):
        """Apply Old Tax Regime to TDS record"""
        self.ensure_one()
        if not self.old_regime_slab_id:
            raise UserError('Old regime slab not found.')
        
        self.hr_tds_id.write({
            'tax_regime_slab': self.old_regime_slab_id.id,
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Regime Updated',
                'message': 'Old Tax Regime has been applied. Please click "Recompute TDS" to update calculations.',
                'type': 'success',
                'sticky': False,
            },
        }
    
    def action_select_new_regime(self):
        """Apply New Tax Regime to TDS record"""
        self.ensure_one()
        if not self.new_regime_slab_id:
            raise UserError('New regime slab not found.')
        
        self.hr_tds_id.write({
            'tax_regime_slab': self.new_regime_slab_id.id,
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Regime Updated',
                'message': 'New Tax Regime has been applied. Please click "Recompute TDS" to update calculations.',
                'type': 'success',
                'sticky': False,
            },
        }
