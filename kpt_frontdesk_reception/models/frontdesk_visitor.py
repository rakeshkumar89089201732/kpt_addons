from odoo import fields, models


class FrontdeskVisitor(models.Model):
    _inherit = "frontdesk.visitor"

    selfie_image = fields.Image(
        string="Check-In Selfie",
        attachment=True,
        max_width=1024,
        max_height=1024,
    )
