# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    auto_save_draft_enabled = fields.Boolean(
        string="Enable Autosave (Draft)",
        config_parameter="auto_save_draft.enabled",
        default=True,
    )
    auto_save_draft_initial_delay_ms = fields.Integer(
        string="Initial delay (ms)",
        config_parameter="auto_save_draft.initial_delay_ms",
        default=120000,
        help="Delay before the first periodic autosave starts for existing records.",
    )
    auto_save_draft_regular_interval_ms = fields.Integer(
        string="Interval (ms)",
        config_parameter="auto_save_draft.regular_interval_ms",
        default=240000,
        help="Periodic autosave interval when there are unsaved changes.",
    )

