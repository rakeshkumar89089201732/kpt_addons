# -*- coding: utf-8 -*-

from odoo import models, fields

class GlobalAccountCategory(models.Model):
    _name = 'global.account.category'
    _description = 'Global Account Category'
    _order = 'name'

    name = fields.Char(string='Category Name', required=True, translate=True)
