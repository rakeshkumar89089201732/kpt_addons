from odoo import models, fields, api
from odoo.osv import expression

class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f'{rec.pricelist_id.name} ({rec.fixed_price} Price)'



class ProductTemplate(models.Model):
    _inherit = "product.template"


    account_income_intrastate_id = fields.Many2one('account.account',
        string="IntraState Income Account",
        help="This account will be used when validating a customer invoice.")


    account_income_interstate_id = fields.Many2one('account.account',
        string="InterState Income Account",
        help="This account will be used when validating a customer invoice.")


    account_expense_intrastate_id = fields.Many2one('account.account',
        string="IntraState Expense Account",
        help="Keep this field empty to use the default value from the product category. If anglo-saxon accounting with automated valuation method is configured, the expense account on the product category will be used.")

    account_expense_interstate_id = fields.Many2one('account.account',
        string="InterState Expense Account",
        help="Keep this field empty to use the default value from the product category. If anglo-saxon accounting with automated valuation method is configured, the expense account on the product category will be used.")

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
