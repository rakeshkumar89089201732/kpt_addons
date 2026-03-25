from odoo import api, fields, models
from odoo.exceptions import UserError


class HrContract(models.Model):
    _inherit = 'hr.contract'

    pan_lookup = fields.Char(string='PAN Lookup', copy=False)

    def action_verify_employee_pan(self):
        for contract in self:
            if not contract.employee_id:
                raise UserError('Please select an Employee first.')
            if not contract.employee_id.pan_number:
                raise UserError('Employee PAN Number is empty.')
            contract.employee_id.action_verify_pan()
        return True

    def action_fetch_employee_by_pan(self):
        for contract in self:
            pan = (contract.pan_lookup or '').strip().upper()
            if not pan:
                raise UserError('Please enter PAN in PAN Lookup.')

            employee = self.env['hr.employee'].search([('pan_number', '=', pan)], limit=1)
            if employee:
                contract.employee_id = employee.id
                continue

            allow_create = self.env['ir.config_parameter'].sudo().get_param('hr_pan_verification.allow_employee_create')
            if str(allow_create).lower() not in ('1', 'true', 'yes'):
                raise UserError('No employee found for this PAN. Enable employee creation from PAN in Settings to create.')

            res = self.env['hr.pan.verification.client'].verify_pan(pan)
            name = res.get('name')
            if not name:
                raise UserError('PAN verified but name was not returned by the API.')

            employee = self.env['hr.employee'].create({
                'name': name,
                'pan_number': pan,
                'pan_verified_name': name,
                'pan_verification_status': 'verified',
                'pan_last_verified': fields.Datetime.now(),
                'pan_verification_raw': res.get('raw') or False,
            })
            contract.employee_id = employee.id
        return True

    @api.onchange('pan_lookup')
    def _onchange_pan_lookup(self):
        for contract in self:
            pan = (contract.pan_lookup or '').strip().upper()
            if pan and len(pan) == 10:
                employee = self.env['hr.employee'].search([('pan_number', '=', pan)], limit=1)
                if employee:
                    contract.employee_id = employee.id
