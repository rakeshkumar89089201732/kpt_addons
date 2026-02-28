from odoo import models, fields, api

class TDSChallan(models.Model):
    _name = 'tds.challan'
    _description = 'TDS Challan'

    _sql_constraints = [
        ('unique_company_month', 'unique(company_id, period_month)', 'Only one challan is allowed per company per month.'),
    ]

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    period_month = fields.Date(
        string='Challan Month',
        required=True,
        index=True,
        help='Select the month (use the first day of the month). Used to auto-fill challan amount from HR TDS month-wise data.',
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )

    tds_payment = fields.Float("TDS Payment")
    surcharge = fields.Float("Surcharge")
    education_cess = fields.Float("Education Cess")
    higher_education_cess = fields.Float("Higher Education Cess")
    interest = fields.Float("Interest")
    other = fields.Float("Other")
    fee = fields.Float("Fee")
    cheque_dd_no = fields.Char("Cheque / DD No")
    bsr_code = fields.Char("BSR Code")
    tax_deposit_date = fields.Date("Date on which Tax Deposited")
    challan_no = fields.Char("Transfer Voucher / Challan No.")
    book_entry = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')
    ], string="Whether TDS Deposited by Book Entry?")
    minor_head = fields.Char("Minor Head")

    line_ids = fields.One2many('tds.challan.line', 'challan_id', string="TDS Details")

    @api.onchange('company_id')
    def _onchange_company_id_set_defaults(self):
        for rec in self:
            if rec.company_id and not rec.bsr_code:
                rec.bsr_code = rec.company_id.bsr_code or ''

    def action_autofill_from_hr_tds(self):
        self.ensure_one()
        if not self.period_month:
            return

        # Auto-fill challan amount based on HR TDS month-wise lines for the selected month.
        month_label = self.period_month.strftime('%B')
        month_name = month_label.lower()
        year = str(self.period_month.year)
        month_year = f"{month_label} {year}"

        domain = [
            ('months', '=', month_name),
            ('tds_month_year', '=', month_year),
            ('is_previous_employer', '=', False),
        ]
        if self.company_id:
            domain.append(('hr_tds_id.hr_employee_id.company_id', '=', self.company_id.id))

        lines = self.env['month.wise.tds'].search(domain)
        self.tds_payment = float(sum(lines.mapped('tds_month_amt')) or 0.0)
        
        # Clear existing lines
        self.line_ids = [(5, 0, 0)]
        
        # Create lines from month.wise.tds
        new_lines = []
        for line in lines:
            new_lines.append((0, 0, {
                'employee_id': line.hr_tds_id.hr_employee_id.id,
                'tds_amount': line.tds_month_amt,
                'date': self.period_month, # Default to challan month
            }))
        self.line_ids = new_lines

        if self.company_id and not self.bsr_code:
            self.bsr_code = self.company_id.bsr_code or ''
