from odoo import models, fields, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class RentPaymentLine(models.Model):
    _name = 'rent.payment.line'
    _description = 'Rent Payment Line'
    _order = 'period_from'

    hr_tds_id = fields.Many2one('hr.tds', string='TDS Record', required=True, ondelete='cascade')
    period_from = fields.Date('Period From', required=True, help='Start date of rent payment period')
    period_to = fields.Date('Period To', required=True, help='End date of rent payment period')
    monthly_rent = fields.Float('Monthly Rent', required=True, help='Monthly rent amount for this period')
    landlord_name = fields.Char('Landlord Name', help='Name of the property owner')
    landlord_pan = fields.Char('Landlord PAN', help='PAN of landlord (mandatory if annual rent > ₹1,00,000)')
    property_address = fields.Text('Property Address', help='Address of rented property')
    city_type = fields.Selection([
        ('metro', 'Metro City (Mumbai, Delhi, Kolkata, Chennai, Bangalore, Hyderabad)'),
        ('non_metro', 'Non-Metro City')
    ], string='City Type', default='non_metro', required=False, help='Metro or Non-Metro affects HRA exemption %')
    number_of_months = fields.Float('Number of Months', compute='_compute_number_of_months', store=True, help='Number of months in this rent period')
    total_rent_paid = fields.Float('Total Rent for Period', compute='_compute_total_rent_paid', store=True, help='Total rent paid for this period')
    hra_exemption = fields.Float('HRA Exemption', help='Calculated HRA exemption for this period (manual override possible)')

    @api.depends('period_from', 'period_to')
    def _compute_number_of_months(self):
        for line in self:
            if line.period_from and line.period_to:
                delta = relativedelta(line.period_to, line.period_from)
                months = (delta.years * 12) + delta.months
                if line.period_to.day >= line.period_from.day:
                    months += 1
                line.number_of_months = max(months, 0)
            else:
                line.number_of_months = 0

    @api.depends('monthly_rent', 'number_of_months')
    def _compute_total_rent_paid(self):
        for line in self:
            line.total_rent_paid = line.monthly_rent * line.number_of_months

    @api.constrains('period_from', 'period_to')
    def _check_dates(self):
        for line in self:
            if line.period_from and line.period_to and line.period_from > line.period_to:
                raise ValidationError('Period From date must be before Period To date.')
            
            # Check for overlapping periods within the same TDS record
            if line.hr_tds_id:
                overlapping = self.search([
                    ('hr_tds_id', '=', line.hr_tds_id.id),
                    ('id', '!=', line.id),
                    '|',
                    '&', ('period_from', '<=', line.period_from), ('period_to', '>=', line.period_from),
                    '&', ('period_from', '<=', line.period_to), ('period_to', '>=', line.period_to)
                ])
                if overlapping:
                    raise ValidationError('Rent periods cannot overlap. Please check the dates.')

    @api.constrains('monthly_rent', 'landlord_pan', 'total_rent_paid')
    def _check_rent_pan(self):
        for line in self:
            if line.monthly_rent < 0:
                raise ValidationError('Monthly rent cannot be negative.')
            
            # PAN mandatory if annual rent exceeds ₹1,00,000
            annual_rent = line.monthly_rent * 12
            if annual_rent > 100000 and not line.landlord_pan:
                raise ValidationError('Landlord PAN is mandatory when annual rent exceeds ₹1,00,000 as per Income Tax rules.')

    @api.onchange('monthly_rent', 'landlord_pan')
    def _onchange_rent_pan_warning(self):
        for line in self:
            if not line.monthly_rent:
                continue
            annual_rent = (line.monthly_rent or 0.0) * 12
            if annual_rent > 100000 and not line.landlord_pan:
                return {
                    'warning': {
                        'title': 'PAN Required',
                        'message': 'Landlord PAN is mandatory when annual rent exceeds ₹1,00,000 as per Income Tax rules.'
                    }
                }

    @api.onchange('period_from')
    def _onchange_period_from(self):
        """Auto-set period_to to end of FY if not set"""
        if self.period_from and not self.period_to and self.hr_tds_id:
            self.period_to = self.hr_tds_id.tds_to_date
