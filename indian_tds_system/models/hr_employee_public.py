from odoo import models, fields


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    # Minimal stubs so these fields exist on the public employee profile.
    # Values are not used in self-service screens; the real data lives on hr.employee.
    pan_number = fields.Char(string="PAN Number", groups="hr.group_hr_user")
    aadhar_number = fields.Char(string="Aadhar Number", groups="hr.group_hr_user")
    tds_category_code = fields.Selection(
        [
            ("W", "Woman"),
            ("S", "Senior Citizen"),
            ("O", "Super Senior Citizen"),
            ("G", "Other"),
        ],
        string="TDS Category",
        groups="hr.group_hr_user",
    )

