# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OfferLetterTemplate(models.Model):
    """
    Offer Letter Template — defines reusable content blocks for offer letters.

    Changes from original:
    - Removed the SQL unique constraint (job_id, company_id) which prevented
      creating more than one template per job position. Multiple templates per
      job are now allowed.
    - Added `is_default` boolean: only ONE template per (job_id, company_id)
      can have is_default=True (enforced via Python constraint).
    - Added `letter_title` for customizable PDF subject/heading.
    - Added `show_salary_table` toggle to control salary table in PDF.
    - Added `show_acceptance_block` toggle to control acceptance block in PDF.
    - Added `custom_footer_text` for a custom PDF footer line.
    """
    _name = 'offer.letter.template'
    _description = 'Offer Letter Template'
    _order = 'sequence, name'

    def init(self):
        """
        Defensive schema sync:
        some environments may have this module code updated without a proper
        module upgrade, leading to missing columns (e.g. `is_default`).
        Ensure required columns exist to avoid runtime RPC errors.
        """
        cr = self.env.cr
        table = self._table  # offer_letter_template
        cr.execute(
            """
            SELECT 1
              FROM information_schema.columns
             WHERE table_name = %s
               AND column_name = 'is_default'
            """,
            [table],
        )
        if not cr.fetchone():
            cr.execute(f'ALTER TABLE "{table}" ADD COLUMN is_default boolean DEFAULT false')
            cr.execute(f'UPDATE "{table}" SET is_default = false WHERE is_default IS NULL')

    name = fields.Char(
        string='Template Name',
        required=True,
        tracking=True,
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
    is_default = fields.Boolean(
        string='Is Default',
        default=False,
        help='If checked, this template will be auto-selected when creating an '
             'offer for this job position. Only one template per job position per '
             'company can be the default.',
        tracking=True,
    )
    job_id = fields.Many2one(
        'hr.job',
        string='Job Position',
        required=True,
        tracking=True,
        help='This template can be used for offers for this job position',
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='job_id.department_id',
        store=True,
        readonly=True,
    )

    # ---------------------
    # PDF Customization
    # ---------------------
    letter_title = fields.Char(
        string='Letter Title / Subject',
        default='OFFER OF APPOINTMENT',
        help='The main heading / subject line shown on the PDF offer letter. '
             'Example: "OFFER OF APPOINTMENT", "APPOINTMENT LETTER".',
    )
    show_salary_table = fields.Boolean(
        string='Show Salary Table',
        default=True,
        help='If unchecked, the salary breakdown table will NOT appear in the printed PDF.',
    )
    show_acceptance_block = fields.Boolean(
        string='Show Acceptance Block',
        default=True,
        help='If unchecked, the candidate acceptance signature section will NOT appear in the PDF.',
    )
    custom_footer_text = fields.Char(
        string='Custom Footer Text',
        help='Optional custom text shown in the PDF footer. Leave blank to use the default '
             'company name + website footer.',
    )

    # ---------------------
    # Template Content
    # ---------------------
    introduction_text = fields.Html(
        string='Introduction Text',
        default='''<p>We are pleased to offer you the position of <strong>[POSITION]</strong> in our <strong>[DEPARTMENT]</strong> department.</p>
<p>We believe your skills and experience will be a valuable addition to our team.</p>''',
        help='Introduction paragraph for the offer letter. Use [POSITION], [DEPARTMENT], [CANDIDATE_NAME] as placeholders.',
    )

    roles_responsibilities = fields.Html(
        string='Roles & Responsibilities',
        required=True,
        help='Define the key roles and responsibilities for this position',
    )

    reporting_structure = fields.Html(
        string='Reporting Structure',
        help='Define reporting hierarchy and team structure',
    )

    work_location = fields.Char(
        string='Work Location',
        help='Primary work location for this position',
    )

    work_hours = fields.Char(
        string='Work Hours',
        default='9:00 AM - 6:00 PM (Monday to Friday)',
        help='Standard work hours for this position',
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
        help='List of benefits and perks offered',
    )

    additional_terms = fields.Html(
        string='Additional Terms',
        help='Any additional terms and conditions specific to this position',
    )

    terms_conditions = fields.Html(
        string='General Terms & Conditions',
        default='''<ul>
<li>This offer is subject to successful background verification</li>
<li>Medical fitness certificate is required before joining</li>
<li>Submission of all required documents (ID proof, address proof, educational certificates)</li>
<li>This is a full-time employment position</li>
<li>You will be required to sign a confidentiality and non-disclosure agreement</li>
</ul>''',
        help='General terms and conditions applicable to all offers',
    )

    closing_text = fields.Html(
        string='Closing Text',
        default='''<p>We look forward to welcoming you to our team and are confident that you will make significant contributions to our organization.</p>
<p>Please confirm your acceptance of this offer by signing and returning a copy of this letter.</p>''',
        help='Closing paragraph for the offer letter',
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )

    # ---------------------
    # Original SQL constraint removed — was:
    # _sql_constraints = [
    #     ('job_company_unique', 'unique(job_id, company_id)',
    #      'Only one template per job position per company is allowed!'),
    # ]
    # Replaced with a Python constraint below that only blocks duplicate DEFAULTS.
    # ---------------------

    @api.constrains('is_default', 'job_id', 'company_id')
    def _check_default_unique(self):
        """
        Ensure only ONE template per (job_id, company_id) has is_default=True.
        Multiple non-default templates per job are fully allowed.
        """
        for template in self:
            if template.is_default:
                duplicate = self.search([
                    ('job_id', '=', template.job_id.id),
                    ('company_id', '=', template.company_id.id),
                    ('is_default', '=', True),
                    ('id', '!=', template.id),
                    ('active', '=', True),
                ])
                if duplicate:
                    raise ValidationError(_(
                        'Only one default template per job position per company is allowed. '
                        'Template "%s" is already set as default for job "%s".'
                    ) % (duplicate[0].name, template.job_id.name))

    @api.constrains('probation_period', 'notice_period')
    def _check_periods(self):
        for template in self:
            if template.probation_period < 0:
                raise ValidationError(_('Probation period cannot be negative.'))
            if template.notice_period < 0:
                raise ValidationError(_('Notice period cannot be negative.'))

    def name_get(self):
        result = []
        for template in self:
            name = '%s - %s' % (template.job_id.name, template.name)
            if template.is_default:
                name += ' ★'
            result.append((template.id, name))
        return result
