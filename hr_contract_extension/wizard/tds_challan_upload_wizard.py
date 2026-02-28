from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
try:
    import openpyxl
except ImportError:
    openpyxl = None

class TdsChallanUploadWizard(models.TransientModel):
    _name = 'tds.challan.upload.wizard'
    _description = 'TDS Challan Upload Wizard'

    file = fields.Binary(string='Excel File', required=True)
    filename = fields.Char(string='Filename')
    challan_id = fields.Many2one('tds.challan', string='Challan', required=True, default=lambda self: self.env.context.get('active_id'))

    def action_upload(self):
        self.ensure_one()
        if not openpyxl:
            raise UserError(_("Please install openpyxl to import Excel files."))

        try:
            file_data = base64.b64decode(self.file)
            workbook = openpyxl.load_workbook(io.BytesIO(file_data), data_only=True)
            sheet = workbook.active
        except Exception as e:
            raise UserError(_("Invalid file! Please upload a valid Excel file.\nError: %s") % str(e))

        lines_to_create = []
        # Assuming header is in first row
        # Columns: Employee Code (A), PAN (B), TDS Amount (C), Date (D)
        
        row_idx = 0
        for row in sheet.iter_rows(min_row=2, values_only=True):
            row_idx += 1
            # Skip empty rows
            if not any(row):
                continue
            
            emp_code = str(row[0]).strip() if row[0] else ''
            pan_no = str(row[1]).strip() if len(row) > 1 and row[1] else ''
            tds_amount = row[2] if len(row) > 2 else 0.0
            date_val = row[3] if len(row) > 3 else False

            if not emp_code:
                continue

            # Find employee
            employee = self.env['hr.employee'].search([
                '|', ('registration_number', '=', emp_code), ('barcode', '=', emp_code)
            ], limit=1)
            
            if not employee:
                # Try searching by name if code fails? No, risky. 
                # Let's try searching by PAN if code fails and PAN is provided
                if pan_no:
                    employee = self.env['hr.employee'].search([('pan_number', '=', pan_no)], limit=1)
            
            if not employee:
                raise UserError(_("Employee not found for code: %s (Row %d)") % (emp_code, row_idx + 1))

            # Validate Date
            line_date = self.challan_id.period_month
            if date_val:
                if isinstance(date_val, str):
                    try:
                        line_date = fields.Date.from_string(date_val)
                    except:
                        pass
                elif hasattr(date_val, 'date'): # datetime object
                    line_date = date_val.date()
                elif hasattr(date_val, 'strftime'): # date object
                     line_date = date_val
            
            lines_to_create.append({
                'challan_id': self.challan_id.id,
                'employee_id': employee.id,
                'tds_amount': float(tds_amount) if tds_amount else 0.0,
                'date': line_date,
            })

        if lines_to_create:
            # Clear existing lines? Maybe ask user? For now, append.
            # Or better, if uploading, maybe we want to replace or update?
            # User requirement: "upload employee wise tds return deatils".
            # Usually uploads might replace or append. Let's append for safety, user can delete.
            self.env['tds.challan.line'].create(lines_to_create)
            
            # Update parent total?
            # self.challan_id.tds_payment = sum(line['tds_amount'] for line in lines_to_create)
            # Re-compute total from all lines
            total = sum(self.challan_id.line_ids.mapped('tds_amount'))
            self.challan_id.tds_payment = total

        return {'type': 'ir.actions.act_window_close'}
