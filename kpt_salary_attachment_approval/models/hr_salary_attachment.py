from odoo import api, fields, models, _


class HrSalaryAttachment(models.Model):
    _inherit = "hr.salary.attachment"

    # Add an intermediate approval state. Payroll logic only processes records in state 'open',
    # so attachments in 'to_approve' will not impact payslips until approved.
    state = fields.Selection(
        selection_add=[("to_approve", "To Approve")],
        ondelete={"to_approve": "set default"},
        default="to_approve",
    )

    def action_submit_for_approval(self):
        for attachment in self:
            if attachment.state in ("open", "cancel", "close"):
                # If already processed, do not go back to approval
                continue
            attachment.state = "to_approve"

    def action_approve(self):
        for attachment in self:
            if attachment.state != "to_approve":
                continue
            attachment.state = "open"

    def action_reject(self):
        for attachment in self:
            if attachment.state != "to_approve":
                continue
            attachment.state = "cancel"

