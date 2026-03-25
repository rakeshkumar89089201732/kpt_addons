# -*- coding: utf-8 -*-

from odoo import api, models


class AutoSaveDraftConfig(models.AbstractModel):
    _name = "auto.save.draft.config"
    _description = "Auto Save Draft Config"

    @api.model
    def get_params(self):
        """Return autosave params (sudo) for the web client."""
        param = self.env["ir.config_parameter"].sudo()
        return {
            "enabled": param.get_param("auto_save_draft.enabled", "1") in ("1", "True", "true"),
            "initial_delay_ms": int(param.get_param("auto_save_draft.initial_delay_ms", "120000") or 120000),
            "regular_interval_ms": int(param.get_param("auto_save_draft.regular_interval_ms", "240000") or 240000),
        }

