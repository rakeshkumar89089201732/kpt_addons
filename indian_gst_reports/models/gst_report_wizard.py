# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
import json
import io
import base64

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

class GstReportWizard(models.TransientModel):
    _name = 'gst.report.wizard'
    _description = 'Indian GST Report Wizard'

    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    report_type = fields.Selection([
        ('gstr1', 'GSTR-1 (Outward Supplies)'),
        ('gstr2', 'GSTR-2 (Inward Supplies)'),
        ('gstr3b', 'GSTR-3B (Monthly Summary)'),
        ('gstr9', 'GSTR-9 (Annual Return)'),
    ], string='Report Type', required=True, default='gstr1')
    
    gst_report_file = fields.Binary('GST Report')
    file_name = fields.Char('File Name')

    def action_generate_report(self):
        if not xlsxwriter:
            raise ValidationError(_("The 'xlsxwriter' library is required to generate Excel reports. Please install it with 'pip install XlsxWriter'."))

        self.ensure_one()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        if self.report_type == 'gstr1':
            self.generate_gstr1(workbook)
        elif self.report_type == 'gstr2':
            self.generate_gstr2(workbook)
        elif self.report_type == 'gstr3b':
            self.generate_gstr3b(workbook)
        elif self.report_type == 'gstr9':
            self.generate_gstr9(workbook)
            
        workbook.close()
        output.seek(0)
        
        file_data = base64.b64encode(output.read())
        self.write({
            'gst_report_file': file_data,
            'file_name': f"{self.report_type}_{self.date_from}_{self.date_to}.xlsx"
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'gst.report.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def generate_gstr1(self, workbook):
        worksheet = workbook.add_worksheet('B2B')
        worksheet.write('A1', 'Sample GSTR-1 Data (B2B)')
        # TODO: Implement full logic

    def generate_gstr2(self, workbook):
        worksheet = workbook.add_worksheet('B2B')
        worksheet.write('A1', 'Sample GSTR-2 Data')

    def generate_gstr3b(self, workbook):
        worksheet = workbook.add_worksheet('GSTR-3B')
        worksheet.write('A1', 'Sample GSTR-3B Data')

    def generate_gstr9(self, workbook):
        worksheet = workbook.add_worksheet('GSTR-9')
        worksheet.write('A1', 'Sample GSTR-9 Data')
