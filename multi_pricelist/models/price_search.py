from odoo import models, api , fields
from odoo.osv import expression


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            keywords = name.split()
            name_domain = []
            if len(keywords) > 1:
                name_domain = ['&']
            for keyword in keywords:
                name_domain.append(('name', operator, keyword))
            domain = expression.AND([name_domain, domain])
        return self._search(domain, limit=limit, order=order)


class StockMove(models.Model):
    _inherit = 'stock.move'

    product_price = fields.Float(string="product price")
