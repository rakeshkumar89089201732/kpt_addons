from odoo import models, fields, api

class TDSChallanLine(models.Model):
    _name = 'tds.challan.line'
    _description = 'TDS Challan Line'

    challan_id = fields.Many2one('tds.challan', string='Challan', ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    pan_no = fields.Char(string='PAN No', related='employee_id.pan_number', store=True)
    tds_amount = fields.Float(string='TDS Amount', required=True)
    date = fields.Date(string='Date')
