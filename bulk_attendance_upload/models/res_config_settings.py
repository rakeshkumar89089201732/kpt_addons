# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    attendance_kiosk_menu_visible = fields.Boolean(
        string="Kiosk Mode menu visible",
        compute="_compute_attendance_kiosk_menu_visible",
        readonly=True,
    )

    @api.depends_context('company')
    def _compute_attendance_kiosk_menu_visible(self):
        menu = self.env.ref('hr_attendance.menu_hr_attendance_kiosk_no_user_mode', raise_if_not_found=False)
        for rec in self:
            rec.attendance_kiosk_menu_visible = menu.active if menu else True

    def action_disable_kiosk_menu(self):
        """Hide the Kiosk Mode menu from the Attendances module."""
        menu = self.env.ref('hr_attendance.menu_hr_attendance_kiosk_no_user_mode', raise_if_not_found=False)
        if menu:
            menu.sudo().write({'active': False})
        self.invalidate_recordset(['attendance_kiosk_menu_visible'])
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_enable_kiosk_menu(self):
        """Show the Kiosk Mode menu in the Attendances module."""
        menu = self.env.ref('hr_attendance.menu_hr_attendance_kiosk_no_user_mode', raise_if_not_found=False)
        if menu:
            menu.sudo().write({'active': True})
        self.invalidate_recordset(['attendance_kiosk_menu_visible'])
        return {'type': 'ir.actions.client', 'tag': 'reload'}
