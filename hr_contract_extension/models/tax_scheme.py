from odoo import models, fields, api


class TdsSection(models.Model):
    _name = 'tds.section'
    _description = 'Tds Section'

    name = fields.Char('Section Name')
    tds_schemes_ids = fields.One2many('tds.section.scheme', 'section_id')

class TdsSectionScheme(models.Model):
    _name = 'tds.section.scheme'
    _description = 'Tds Section Scheme'

    _rec_name = 'scheme_name'


    section_id = fields.Many2one('tds.section')
    scheme_name = fields.Char('Investment/Scheme')

    scheme_details = fields.Char('Scheme Details')
    type_of_deduction = fields.Selection([('amount', 'Amount'), ('percentage', 'Percentage %')], string='Deduction Type')
    max_limit_deduction = fields.Float('Max Limit Deduction')
    applicable_regime = fields.Selection([
        ('both', 'Both Regimes'),
        ('old', 'Old Regime Only'),
        ('new', 'New Regime Only')
    ], string='Applicable In', default='old', required=True, 
       help='Old Regime: All deductions allowed\nNew Regime: Only Standard Deduction, 80CCD(2), Family Pension allowed')


    def name_get(self):
        res = []
        for rec in self:
            scheme = (rec.scheme_name or '').strip()
            regime_label = ''
            if rec.applicable_regime == 'old':
                regime_label = ' [Old Regime]'
            elif rec.applicable_regime == 'new':
                regime_label = ' [New Regime]'
            name = f"{scheme}{regime_label}" if scheme else (regime_label.strip() or 'Scheme')
            res.append((rec.id, name))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=80):
        args = list(args or [])
        if name:
            domain = ['|', '|',
                      ('scheme_name', operator, name),
                      ('scheme_details', operator, name),
                      ('section_id.name', operator, name)]
            recs = self.search(domain + args, limit=limit)
        else:
            recs = self.search(args, limit=limit)
        return recs.name_get()


    def _compute_display_name(self):
        for rec in self:
            regime_label = ''
            if rec.applicable_regime == 'old':
                regime_label = ' [Old Regime]'
            elif rec.applicable_regime == 'new':
                regime_label = ' [New Regime]'
            rec.display_name = f'{rec.scheme_name}{regime_label}'
