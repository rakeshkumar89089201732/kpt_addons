from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta

class TaxSlab(models.Model):
    _name = 'tax.slab'
    _description = 'Tax Slab'


    name = fields.Char(string='Regime Name')
    active = fields.Boolean(default=True)
    help_url = fields.Char(string='Help URL')
    help_link_ids = fields.One2many('tax.slab.help.link', 'tax_slab_id', string='Help Links')
    help_link_count = fields.Integer(compute='_compute_help_link_count', store=False)
    financial_year_name = fields.Char(string="Financial Year", help="Example: 2024-2025")
    date_start = fields.Date(string="FY Start Date", required=True)
    date_end = fields.Date(string="FY End Date", required=True)
    tax_regime_type = fields.Selection([
        ('old', 'Old Tax Regime'),
        ('new', 'New Tax Regime (u/s 115BAC)')
    ], string='Regime Type', required=True, default='new', help='Select Old or New tax regime as per Income Tax Act')
    allowed_scheme_ids = fields.Many2many(
        'tds.section.scheme',
        'tax_slab_tds_scheme_rel',
        'tax_slab_id',
        'scheme_id',
        string='Allowed Deduction Schemes',
        help='If set, only these schemes will be available in TDS deduction lines when this Tax Slab is selected.'
    )
    tax_regime_line_ids = fields.One2many('tax.slab.line', 'tax_regime_id', string='Tax Slab lines', store=True)
    age_classification = fields.Selection([
        ('regular', 'Regular Citizen (Below 60)'),
        ('senior', 'Senior Citizen (60-79 Years)'),
        ('super_senior', 'Super Senior Citizen(80+ Years)')],
        string="Age Classification",  default='regular')

    enable_rebate_87a = fields.Boolean(string='Enable Rebate u/s 87A', default=False)
    rebate_87a_income_limit = fields.Float(string='87A Income Limit')
    rebate_87a_amount = fields.Float(string='87A Rebate Amount')

    @api.constrains('enable_rebate_87a', 'rebate_87a_income_limit', 'rebate_87a_amount')
    def _check_rebate_87a_config(self):
        for rec in self:
            if not rec.enable_rebate_87a:
                continue
            if (rec.rebate_87a_income_limit or 0.0) <= 0.0:
                raise ValidationError('87A Income Limit must be greater than 0.')
            if (rec.rebate_87a_amount or 0.0) <= 0.0:
                raise ValidationError('87A Rebate Amount must be greater than 0.')

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = (rec.name or '').strip() or 'Tax Slab'

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})

        if 'tax_regime_line_ids' not in default and self.tax_regime_line_ids:
            default['tax_regime_line_ids'] = [
                (0, 0, line.copy_data()[0])
                for line in self.tax_regime_line_ids
            ]

        if not default.get('name'):
            source_name = (self.name or '').strip() or 'Tax Slab'
            base_name = f"{source_name} (Duplicate)"
            new_name = base_name
            counter = 2
            while self.search_count([('name', '=', new_name)]):
                new_name = f"{base_name} {counter}"
                counter += 1
            default['name'] = new_name

        return super().copy(default)

    @api.depends('help_link_ids')
    def _compute_help_link_count(self):
        for rec in self:
            rec.help_link_count = len(rec.help_link_ids)

    def action_open_help_url(self):
        self.ensure_one()
        if self.help_link_ids:
            if len(self.help_link_ids) == 1:
                return self.help_link_ids.action_open_url()
            tree_view = self.env.ref('hr_contract_extension.view_tax_slab_help_link_tree').id
            form_view = self.env.ref('hr_contract_extension.view_tax_slab_help_link_form').id
            return {
                'type': 'ir.actions.act_window',
                'name': 'Help Links',
                'res_model': 'tax.slab.help.link',
                'view_mode': 'tree,form',
                'views': [(tree_view, 'tree'), (form_view, 'form')],
                'domain': [('tax_slab_id', '=', self.id)],
                'context': {
                    'default_tax_slab_id': self.id,
                },
                'target': 'current',
            }

        if self.help_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.help_url,
                'target': 'new',
            }

        raise ValidationError('Please set Help URL first.')



    @api.onchange("date_start")
    def _onchange_date_start(self):
        """Automatically set name based on date_start"""
        if self.date_start:
            year = self.date_start.year
            self.date_end = self.date_start.replace(year=year + 1) - timedelta(days=1)
            self.financial_year_name = f"{year}-{year + 1}"


class TaxSlabLine(models.Model):
    _name = 'tax.slab.line'
    _description = 'Tax Slab Line'

    tax_regime_id = fields.Many2one('tax.slab', string='Tax Slab')
    tax_regime_description = fields.Char(string='Tax Slab Description')
    tax_regime_per = fields.Float(string='Tax %')
    tax_regime_amt_from = fields.Float(string='Applied From')
    tax_regime_amt_to = fields.Float(string='Applied To')
    surcharge = fields.Float('Surcharge')











