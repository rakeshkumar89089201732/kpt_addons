from odoo import fields, models


class FrontdeskFrontdesk(models.Model):
    _inherit = "frontdesk.frontdesk"

    kpt_enable_reception_animation = fields.Boolean(
        string="Animated Reception Assistant",
        default=True,
        groups="frontdesk.frontdesk_group_user",
        help="Show an animated receptionist with a welcome message on the kiosk.",
    )
    kpt_enable_selfie_check_in = fields.Boolean(
        string="Selfie During Check-In",
        default=True,
        groups="frontdesk.frontdesk_group_user",
        help="Allow visitors to capture or upload a selfie while checking in.",
    )
    kpt_welcome_message = fields.Char(
        string="Reception Message",
        default="Please have a seat. You can register your selfie while checking in.",
        groups="frontdesk.frontdesk_group_user",
    )

    def _get_frontdesk_field(self):
        return super()._get_frontdesk_field() + [
            "kpt_enable_reception_animation",
            "kpt_enable_selfie_check_in",
            "kpt_welcome_message",
        ]
