from odoo import fields, http
from odoo.http import request

from odoo.addons.frontdesk.controllers.main import Frontdesk


class FrontdeskReceptionController(Frontdesk):
    @http.route(
        "/frontdesk/<int:frontdesk_id>/<string:token>/prepare_selfie_visitor_data",
        type="json",
        auth="public",
        methods=["POST"],
    )
    def prepare_selfie_visitor_data(self, frontdesk_id, token, **kwargs):
        frontdesk = request.env["frontdesk.frontdesk"].sudo().browse(frontdesk_id)
        if not frontdesk.exists() or not self._verify_token(frontdesk, token):
            return request.not_found()

        vals = {
            "station_id": frontdesk.id,
            "name": kwargs.get("name"),
            "phone": kwargs.get("phone"),
            "email": kwargs.get("email"),
            "company": kwargs.get("company"),
            "check_in": fields.Datetime.now(),
            "state": "checked_in",
            "host_ids": [(4, host_id) for host_id in kwargs.get("host_ids", [])],
        }
        if kwargs.get("selfie_image"):
            vals["selfie_image"] = kwargs["selfie_image"]

        visitor = request.env["frontdesk.visitor"].sudo().create(vals)
        visitor._notify()
        return {"visitor_id": visitor.id}
