# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class TdsBulkCertificateWizard(models.TransientModel):
    _name = 'tds.bulk.certificate.wizard'
    _description = 'TDS Bulk Certificate Generation Wizard'

    # Selection Criteria
    financial_year = fields.Char(string='Financial Year', required=True)
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    all_employees = fields.Boolean(string='All Employees', default=False)
    
    # Certificate Options
    certificate_date = fields.Date(string='Certificate Date', default=fields.Date.today, required=True)
    auto_issue = fields.Boolean(string='Auto Issue Certificates', default=True)
    
    # Filters
    only_approved_calculations = fields.Boolean(string='Only Approved Calculations', default=True)
    min_tds_amount = fields.Float(string='Minimum TDS Amount', default=0.0)
    
    @api.onchange('all_employees')
    def _onchange_all_employees(self):
        if self.all_employees:
            self.employee_ids = self.env['hr.employee'].search([('active', '=', True)])
        else:
            self.employee_ids = False
    
    def action_generate_certificates(self):
        """Generate TDS certificates in bulk"""
        if not self.employee_ids:
            raise UserError('Please select at least one employee.')
        
        # Find TDS calculations for selected criteria
        domain = [
            ('employee_id', 'in', self.employee_ids.ids),
            ('financial_year', '=', self.financial_year),
        ]
        
        if self.only_approved_calculations:
            domain.append(('state', 'in', ['approved', 'locked']))
        
        if self.min_tds_amount > 0:
            domain.append(('total_tax_liability', '>=', self.min_tds_amount))
        
        calculations = self.env['tds.calculation'].search(domain)
        
        if not calculations:
            raise UserError('No TDS calculations found matching the criteria.')
        
        created_certificates = self.env['tds.certificate']
        
        for calculation in calculations:
            # Check if certificate already exists
            existing = self.env['tds.certificate'].search([
                ('employee_id', '=', calculation.employee_id.id),
                ('financial_year', '=', calculation.financial_year),
                ('calculation_id', '=', calculation.id)
            ])
            
            if existing:
                continue
            
            # Generate certificate
            certificate = self.env['tds.certificate'].generate_from_calculation(calculation.id)
            certificate.certificate_date = self.certificate_date
            
            if self.auto_issue:
                certificate.action_issue_certificate()
            
            created_certificates |= certificate
        
        # Return action to view created certificates
        return {
            'type': 'ir.actions.act_window',
            'name': 'Generated TDS Certificates',
            'res_model': 'tds.certificate',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', created_certificates.ids)],
            'target': 'current',
        }
