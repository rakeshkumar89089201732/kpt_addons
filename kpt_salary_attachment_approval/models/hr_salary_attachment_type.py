from odoo import fields, models


class HrSalaryAttachmentType(models.Model):
    _inherit = "hr.salary.attachment.type"

    show_in_mobile = fields.Boolean(
        string="Show in Mobile App",
        default=True,
        help="If enabled, this expense/attachment type will be visible and selectable in the KPT mobile application.",
    )
