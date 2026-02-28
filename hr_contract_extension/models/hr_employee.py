from odoo import models, fields, api
import re
from odoo.exceptions import ValidationError
from datetime import date


class Employee(models.Model):
    _inherit = 'hr.employee'

    pan_number = fields.Char("PAN Number")
    aadhar_number = fields.Char("Aadhaar Number")
    tds_category_code = fields.Selection([
        ('W', 'Woman'),
        ('S', 'Senior Citizen'),
        ('O', 'Super Senior Citizen'),
        ('G', 'Other'),
    ], string="TDS Category", compute="_compute_tds_category", store=True)

    salary_sheet_attachment_count = fields.Integer(
        string='Salary Sheets',
        compute='_compute_salary_sheet_attachment_count'
    )

    # Report-friendly bank/IFSC (uses employee.ifsc_code when available, else bank_id.bic)
    report_ifsc_code = fields.Char(
        string='IFSC (for report)',
        compute='_compute_report_bank_fields'
    )
    report_bank_acc_number = fields.Char(
        string='Bank Account (for report)',
        compute='_compute_report_bank_fields'
    )

    @api.depends('bank_account_id', 'bank_account_id.bank_id', 'bank_account_id.acc_number')
    def _compute_report_bank_fields(self):
        for emp in self:
            acc = emp.bank_account_id
            emp.report_bank_acc_number = (getattr(emp, 'bank_account_number', None) or '') or (acc.acc_number if acc else '') or ''
            ifsc = getattr(emp, 'ifsc_code', None) or ''
            if not ifsc and acc and acc.bank_id:
                ifsc = getattr(acc.bank_id, 'bic', None) or ''
            emp.report_ifsc_code = ifsc or ''


    @api.model
    def create(self, vals):
        self._validate_pan_aadhar(vals)
        return super().create(vals)

    def write(self, vals):
        self._validate_pan_aadhar(vals)
        return super().write(vals)

    def _validate_pan_aadhar(self, vals):
        # PAN validation
        pan = vals.get('pan_number') or self.pan_number
        if pan:
            pan = pan.upper()
            if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', pan):
                raise ValidationError("Invalid PAN Number format. It should be like 'ABCDE1234F'.")

        # Aadhaar validation
        aadhaar = vals.get('aadhar_number') or self.aadhar_number
        if aadhaar:
            if not re.match(r'^[2-9]{1}[0-9]{11}$', aadhaar):
                raise ValidationError("Invalid Aadhaar Number. It must be a 12-digit number starting with 2-9.")

    @api.depends('gender', 'birthday')
    def _compute_tds_category(self):
        for emp in self:
            if emp.birthday:
                today = date.today()
                age = today.year - emp.birthday.year - ((today.month, today.day) < (emp.birthday.month, emp.birthday.day))
                if age >= 80:
                    emp.tds_category_code = 'O'
                elif age >= 60:
                    emp.tds_category_code = 'S'
            elif emp.gender == 'female':
                emp.tds_category_code = 'W'
            else:
                emp.tds_category_code = 'G'

    def _compute_salary_sheet_attachment_count(self):
        Attachment = self.env['ir.attachment']
        for emp in self:
            emp.salary_sheet_attachment_count = Attachment.search_count([
                ('res_model', '=', 'hr.employee'),
                ('res_id', '=', emp.id),
                ('mimetype', '=', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ])

    def action_open_salary_sheet_wizard(self):
        self.ensure_one()
        action = self.env.ref('hr_contract_extension.action_salary_sheet_report_wizard').read()[0]
        action['context'] = dict(self.env.context, default_employee_ids=[self.id])
        return action

    def action_open_salary_sheet_attachments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Salary Sheets',
            'res_model': 'ir.attachment',
            'view_mode': 'tree,form',
            'domain': [
                ('res_model', '=', 'hr.employee'),
                ('res_id', '=', self.id),
                ('mimetype', '=', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ],
            'context': dict(self.env.context, default_res_model='hr.employee', default_res_id=self.id),
            'target': 'current',
        }

    def action_open_salary_sheet_menu(self):
        self.ensure_one()
        # If sheets already exist, open them directly for better UX.
        if self.salary_sheet_attachment_count:
            return self.action_open_salary_sheet_attachments()

        action = self.env.ref('hr_contract_extension.action_employee_salary_sheet_wizard').read()[0]
        action['context'] = dict(self.env.context, active_id=self.id, default_employee_id=self.id)
        return action