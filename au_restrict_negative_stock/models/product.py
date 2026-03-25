from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    allow_negative_stock = fields.Boolean(string='Allow Negative Stock',help='if checked, negative stock will be allowed for this product')


class ProductCategory(models.Model):
    _inherit = 'product.category'

    allow_negative_stock = fields.Boolean(string='Allow Negative Stock',help='if checked, negative stock will be allowed for this category of products')