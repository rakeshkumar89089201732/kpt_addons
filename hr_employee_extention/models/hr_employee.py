from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    guardian_relation = fields.Selection(
        [
            ('father', 'Father'),
            ('husband', 'Husband'),
        ],
        string='Guardian Relation',
        default='father',
        groups="hr.group_hr_user",
    )
    guardian_name = fields.Char(string='Guardian Name', groups="hr.group_hr_user")

    uan_number = fields.Char(string='UAN Number', groups="hr.group_hr_user")
    esic_number = fields.Char(string='ESIC Number', groups="hr.group_hr_user")
    ifsc_code = fields.Char(string='IFSC Code', groups="hr.group_hr_user")

    @api.onchange('gender', 'marital')
    def _onchange_gender_guardian_relation(self):
        for rec in self:
            # Defaulting logic:
            # - Male: Father
            # - Female: Husband if married/cohabitant, else Father
            if rec.gender == 'male':
                rec.guardian_relation = 'father'
            elif rec.gender == 'female':
                if rec.marital in ['married', 'cohabitant']:
                    rec.guardian_relation = 'husband'
                else:
                    rec.guardian_relation = 'father'
