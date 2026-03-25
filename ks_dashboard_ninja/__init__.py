# -*- coding: utf-8 -*-

from . import models
from . import controllers
from . import lib


def uninstall_hook(env):
    """Uninstall hook for Odoo 17 - cleans up dashboard client actions and menus"""
    for rec in env['ks_dashboard_ninja.board'].search([]):
        rec.ks_dashboard_client_action_id.unlink()
        rec.ks_dashboard_menu_id.unlink()
