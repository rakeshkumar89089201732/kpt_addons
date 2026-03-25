# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date
import logging

_logger = logging.getLogger(__name__)


class EmployeeOffer(models.Model):
    """
    Employee Offer Letter model.

    Changes from original:
    - Added `letter_title` field — customizable PDF heading per offer.
    - Added `offer_valid_till` field — expiry date for the offer.
    - Added `show_salary_table` boolean — toggle salary table on PDF.
    - Added `show_acceptance_block` boolean — toggle acceptance block on PDF.
    - Added `custom_footer_text` field — custom footer line on PDF.
    - Updated `_onchange_template_id` to also copy new template fields.
    - Updated `_onchange_position_id` to prefer the `is_default` template.
    - Added `[OFFER_VALID_TILL]` to `_replace_placeholders`.
    - template_id domain relaxed — no longer restricted to `job_id` so user can
      pick any active template.
    """
    _name = 'employee.offer'
    _description = 'Employee Offer Letter'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Offer Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )
    candidate_name = fields.Char(
        string='Candidate Name',
        required=True,
        tracking=True,
    )
    email = fields.Char(
        string='Email',
        required=True,
        tracking=True,
    )
    phone = fields.Char(
        string='Phone',
        tracking=True,
    )
    position_id = fields.Many2one(
        'hr.job',
        string='Job Position',
        required=True,
        tracking=True,
        domain="[('active', '=', True)]",
    )
    template_id = fields.Many2one(
        'offer.letter.template',
        string='Offer Letter Template',
        tracking=True,
        # Removed job_id restriction — user can now pick any active template
        domain="[('active', '=', True)]",
        help='Select a template to auto-populate offer letter content. '
             'Templates marked with ★ are defaults for the selected job position.',
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='position_id.department_id',
        store=True,
        readonly=True,
    )
    offer_date = fields.Date(
        string='Offer Date',
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    joining_date = fields.Date(
        string='Joining Date',
        required=True,
        tracking=True,
    )
    offer_valid_till = fields.Date(
        string='Offer Valid Till',
        tracking=True,
        help='Last date until which this offer is valid. Shown on the PDF.',
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Offer Sent'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, required=True)

    # -------------------------
    # PDF Customization Fields
    # -------------------------
    letter_title = fields.Char(
        string='Letter Title / Subject',
        default='OFFER OF APPOINTMENT',
        help='The main heading / subject line shown on the PDF. '
             'Example: "OFFER OF APPOINTMENT", "APPOINTMENT LETTER".',
        tracking=True,
    )
    show_salary_table = fields.Boolean(
        string='Show Salary Table',
        default=True,
        help='Uncheck to hide the salary breakdown table from the printed PDF.',
    )
    show_acceptance_block = fields.Boolean(
        string='Show Acceptance Block',
        default=True,
        help='Uncheck to hide the candidate acceptance signature section from the PDF.',
    )
    custom_footer_text = fields.Char(
        string='Custom Footer Text',
        help='Optional custom text for the PDF footer. Leave blank to use the '
             'default company name + website footer.',
    )

    # -------------------------
    # Salary Components
    # -------------------------
    basic_salary = fields.Monetary(
        string='Basic Salary',
        currency_field='currency_id',
        required=True,
        tracking=True,
    )
    hra = fields.Monetary(
        string='HRA (House Rent Allowance)',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
    )
    conveyance_allowance = fields.Monetary(
        string='Conveyance Allowance',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
    )
    medical_allowance = fields.Monetary(
        string='Medical Allowance',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
    )
    vehicle_allowance = fields.Monetary(
        string='Vehicle Allowance',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
    )
    washing_allowance = fields.Monetary(
        string='Washing Allowance',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
    )
    other_allowance = fields.Monetary(
        string='Other Allowance',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
    )
    tour_expenses = fields.Monetary(
        string='Tour Expenses',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
    )
    gross_salary = fields.Monetary(
        string='Gross Salary (Monthly)',
        currency_field='currency_id',
        compute='_compute_gross_salary',
        store=True,
        tracking=True,
    )
    ctc_annual = fields.Monetary(
        string='Current CTC (Annual)',
        currency_field='currency_id',
        compute='_compute_ctc',
        store=True,
        tracking=True,
    )
    effective_salary_annual = fields.Monetary(
        string='Effective Salary (FY) Annual',
        currency_field='currency_id',
        compute='_compute_effective_salary',
        store=True,
        tracking=True,
    )

    # Additional Information
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )
    notes = fields.Text(
        string='Notes',
        tracking=True,
    )
    roles_responsibilities = fields.Html(
        string='Roles & Responsibilities',
        help='Key roles and responsibilities for this position',
    )
    reporting_structure = fields.Html(
        string='Reporting Structure',
        help='Reporting hierarchy and team structure',
    )
    work_location = fields.Char(
        string='Work Location',
        help='Primary work location',
    )
    work_hours = fields.Char(
        string='Work Hours',
        help='Standard work hours',
    )
    probation_period = fields.Integer(
        string='Probation Period (Months)',
        default=3,
        help='Probation period in months',
    )
    notice_period = fields.Integer(
        string='Notice Period (Days)',
        default=30,
        help='Notice period in days',
    )
    benefits = fields.Html(
        string='Benefits & Perks',
        help='Benefits and perks offered',
    )
    introduction_text = fields.Html(
        string='Introduction Text',
        help='Introduction paragraph for the offer letter',
    )
    additional_terms = fields.Html(
        string='Additional Terms',
        help='Additional terms specific to this position',
    )
    terms_conditions = fields.Html(
        string='Terms & Conditions',
        default='<p>Please review the offer carefully. This offer is subject to:</p><ul><li>Successful background verification</li><li>Medical fitness certificate</li><li>Submission of required documents</li></ul>',
    )
    closing_text = fields.Html(
        string='Closing Text',
        help='Closing paragraph for the offer letter',
    )

    # Related Records
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        readonly=True,
        tracking=True,
    )
    contract_id = fields.Many2one(
        'hr.contract',
        string='Contract',
        readonly=True,
        tracking=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='Responsible',
        default=lambda self: self.env.user,
        tracking=True,
    )

    # Acceptance/Rejection Details
    acceptance_date = fields.Datetime(
        string='Acceptance Date',
        readonly=True,
        tracking=True,
    )
    rejection_date = fields.Datetime(
        string='Rejection Date',
        readonly=True,
        tracking=True,
    )
    rejection_reason = fields.Text(
        string='Rejection Reason',
        tracking=True,
    )

    @api.depends('basic_salary', 'hra', 'conveyance_allowance', 'medical_allowance',
                 'vehicle_allowance', 'washing_allowance', 'other_allowance', 'tour_expenses')
    def _compute_gross_salary(self):
        for offer in self:
            offer.gross_salary = (
                offer.basic_salary +
                offer.hra +
                offer.conveyance_allowance +
                offer.medical_allowance +
                offer.vehicle_allowance +
                offer.washing_allowance +
                offer.other_allowance +
                offer.tour_expenses
            )

    @api.depends('gross_salary')
    def _compute_ctc(self):
        for offer in self:
            offer.ctc_annual = offer.gross_salary * 12

    @api.depends('gross_salary')
    def _compute_effective_salary(self):
        for offer in self:
            # Effective salary can be same as CTC or adjusted based on company policy
            offer.effective_salary_annual = offer.gross_salary * 12

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('employee.offer') or _('New')
        return super(EmployeeOffer, self).create(vals)

    def action_send_offer(self):
        """Send the offer letter"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft offers can be sent.'))
        self.write({'state': 'sent'})
        message = _('Offer letter sent to %s') % self.candidate_name
        self.message_post(body=message)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_accept_offer(self):
        """Accept the offer and create employee, position, and contract"""
        self.ensure_one()
        if self.state != 'sent':
            raise UserError(_('Only sent offers can be accepted.'))

        # Create Employee
        employee_vals = {
            'name': self.candidate_name,
            'job_id': self.position_id.id,
            'department_id': self.department_id.id if self.department_id else False,
            'work_email': self.email,
            'work_phone': self.phone,
            'company_id': self.company_id.id,
        }
        employee = self.env['hr.employee'].create(employee_vals)

        # Create Contract
        contract_vals = {
            'name': '%s - %s' % (employee.name, self.position_id.name),
            'employee_id': employee.id,
            'job_id': self.position_id.id,
            'department_id': self.department_id.id if self.department_id else False,
            'date_start': self.joining_date,
            'wage': self.gross_salary,
            'state': 'draft',
            'company_id': self.company_id.id,
        }
        contract = self.env['hr.contract'].create(contract_vals)

        # Update offer
        self.write({
            'state': 'accepted',
            'employee_id': employee.id,
            'contract_id': contract.id,
            'acceptance_date': fields.Datetime.now(),
        })

        message = _('Offer accepted. Employee %s and contract created.') % employee.name
        self.message_post(body=message)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Employee Created'),
            'res_model': 'hr.employee',
            'res_id': employee.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_reject_offer(self):
        """Reject the offer"""
        self.ensure_one()
        if self.state not in ['draft', 'sent']:
            raise UserError(_('Only draft or sent offers can be rejected.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Offer'),
            'res_model': 'employee.offer.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_offer_id': self.id},
        }

    def action_cancel_offer(self):
        """Cancel the offer"""
        self.ensure_one()
        if self.state in ['accepted']:
            raise UserError(_('Accepted offers cannot be cancelled.'))
        self.write({'state': 'cancelled'})
        message = _('Offer cancelled.')
        self.message_post(body=message)
        return True

    def action_print_offer_letter(self):
        """Print the offer letter"""
        self.ensure_one()
        return self.env.ref('employee_entry_exit.action_report_offer_letter').report_action(self)

    @api.onchange('position_id')
    def _onchange_position_id(self):
        """
        Auto-select the default template for the selected job position.
        Preference order:
          1. Template with is_default=True for the job
          2. First active template for the job (if only one exists)
          3. Clear (no auto-select if ambiguous and no default set)
        """
        if self.position_id:
            # First try: find the default template for this job
            default_template = self.env['offer.letter.template'].search([
                ('job_id', '=', self.position_id.id),
                ('is_default', '=', True),
                ('active', '=', True),
                ('company_id', '=', self.company_id.id if self.company_id else self.env.company.id),
            ], limit=1)
            if default_template:
                self.template_id = default_template
            else:
                # Second try: if only one template exists for this job, use it
                templates = self.env['offer.letter.template'].search([
                    ('job_id', '=', self.position_id.id),
                    ('active', '=', True),
                ], limit=2)
                if len(templates) == 1:
                    self.template_id = templates[0]
                else:
                    self.template_id = False
        else:
            self.template_id = False

    @api.onchange('template_id')
    def _onchange_template_id(self):
        """
        Populate offer letter content AND PDF settings from the selected template.

        Copies all content fields AND new customization fields:
        letter_title, show_salary_table, show_acceptance_block, custom_footer_text.
        """
        if self.template_id:
            template = self.template_id
            # Content fields
            self.roles_responsibilities = template.roles_responsibilities
            self.reporting_structure = template.reporting_structure
            self.work_location = template.work_location
            self.work_hours = template.work_hours
            self.probation_period = template.probation_period
            self.notice_period = template.notice_period
            self.benefits = template.benefits
            self.introduction_text = template.introduction_text
            self.additional_terms = template.additional_terms
            self.terms_conditions = template.terms_conditions
            self.closing_text = template.closing_text
            # New PDF customization fields
            self.letter_title = template.letter_title or 'OFFER OF APPOINTMENT'
            self.show_salary_table = template.show_salary_table
            self.show_acceptance_block = template.show_acceptance_block
            self.custom_footer_text = template.custom_footer_text or ''

    def _replace_placeholders(self, text):
        """
        Replace placeholder tokens in template text with actual offer values.

        Supported placeholders:
          [CANDIDATE_NAME], [POSITION], [DEPARTMENT], [COMPANY],
          [JOINING_DATE], [OFFER_DATE], [OFFER_VALID_TILL],
          [EMAIL], [PHONE], [WORK_LOCATION], [WORK_HOURS],
          [PROBATION_PERIOD], [NOTICE_PERIOD],
          [BASIC_SALARY], [GROSS_SALARY], [CTC_ANNUAL],
          [RESPONSIBLE_NAME], [COMPANY_ADDRESS], [COMPANY_PHONE], [COMPANY_EMAIL]
        """
        if not text:
            return text

        replacements = {
            '[CANDIDATE_NAME]': self.candidate_name or '',
            '[POSITION]': self.position_id.name if self.position_id else '',
            '[DEPARTMENT]': self.department_id.name if self.department_id else '',
            '[COMPANY]': self.company_id.name if self.company_id else '',
            '[JOINING_DATE]': self.joining_date.strftime('%d %B, %Y') if self.joining_date else '',
            '[OFFER_DATE]': self.offer_date.strftime('%d %B, %Y') if self.offer_date else '',
            '[OFFER_VALID_TILL]': self.offer_valid_till.strftime('%d %B, %Y') if self.offer_valid_till else '',
            '[EMAIL]': self.email or '',
            '[PHONE]': self.phone or '',
            '[WORK_LOCATION]': self.work_location or '',
            '[WORK_HOURS]': self.work_hours or '',
            '[PROBATION_PERIOD]': str(self.probation_period) if self.probation_period else '',
            '[NOTICE_PERIOD]': str(self.notice_period) if self.notice_period else '',
            '[BASIC_SALARY]': '{:,.2f}'.format(self.basic_salary) if self.basic_salary else '',
            '[GROSS_SALARY]': '{:,.2f}'.format(self.gross_salary) if self.gross_salary else '',
            '[CTC_ANNUAL]': '{:,.2f}'.format(self.ctc_annual) if self.ctc_annual else '',
            '[RESPONSIBLE_NAME]': self.user_id.name if self.user_id else '',
            '[COMPANY_ADDRESS]': self._get_company_address(),
            '[COMPANY_PHONE]': self.company_id.phone if self.company_id and self.company_id.phone else '',
            '[COMPANY_EMAIL]': self.company_id.email if self.company_id and self.company_id.email else '',
        }

        result = text
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)
        return result

    def _get_company_address(self):
        """Get formatted company address"""
        if not self.company_id:
            return ''
        company = self.company_id
        address_parts = []
        if company.street:
            address_parts.append(company.street)
        if company.street2:
            address_parts.append(company.street2)
        if company.city:
            address_parts.append(company.city)
        if company.state_id:
            address_parts.append(company.state_id.name)
        if company.zip:
            address_parts.append(company.zip)
        if company.country_id:
            address_parts.append(company.country_id.name)
        return ', '.join(address_parts)

    def get_processed_content(self, field_name):
        """Get field content with placeholders replaced — called from QWeb PDF template"""
        content = getattr(self, field_name, '')
        return self._replace_placeholders(content)

    @api.constrains('joining_date', 'offer_date')
    def _check_joining_date(self):
        for offer in self:
            if offer.joining_date and offer.offer_date:
                if offer.joining_date < offer.offer_date:
                    raise ValidationError(_('Joining date cannot be before offer date.'))

    @api.constrains('offer_valid_till', 'offer_date')
    def _check_valid_till(self):
        for offer in self:
            if offer.offer_valid_till and offer.offer_date:
                if offer.offer_valid_till < offer.offer_date:
                    raise ValidationError(_('Offer valid till date cannot be before the offer date.'))

    @api.constrains('probation_period', 'notice_period')
    def _check_periods(self):
        for offer in self:
            if offer.probation_period < 0:
                raise ValidationError(_('Probation period cannot be negative.'))
            if offer.notice_period < 0:
                raise ValidationError(_('Notice period cannot be negative.'))


class EmployeeOfferRejectWizard(models.TransientModel):
    _name = 'employee.offer.reject.wizard'
    _description = 'Reject Offer Wizard'

    offer_id = fields.Many2one('employee.offer', string='Offer', required=True)
    rejection_reason = fields.Text(string='Rejection Reason', required=True)

    def action_reject(self):
        self.ensure_one()
        self.offer_id.write({
            'state': 'rejected',
            'rejection_reason': self.rejection_reason,
            'rejection_date': fields.Datetime.now(),
        })
        message = _('Offer rejected. Reason: %s') % self.rejection_reason
        self.offer_id.message_post(body=message)
        return {'type': 'ir.actions.act_window_close'}
