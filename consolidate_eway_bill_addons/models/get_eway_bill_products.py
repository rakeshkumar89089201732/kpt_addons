from odoo import models, api, fields, _

class GetProductsEwaybill(models.Model):
    _name = 'get.products.ewaybill'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', related='get_eway_productName')
    product_ids = fields.Many2one(comodel_name='get.ewaybill', string='Get Eway Bill id')
    get_eway_product_itemno = fields.Integer(string="Item No")
    get_eway_product_id = fields.Integer(string="Product Id")
    get_eway_productName = fields.Char(string='productName')
    get_eway_productDesc = fields.Char(string='productDesc')
    get_eway_hsnCode = fields.Char(string='hsnCode')
    get_eway_quantity = fields.Char(string='Orderd quantity')
    get_eway_qtyUnit = fields.Char(string='UOM')
    get_eway_cgstRate = fields.Float(string='CGST')
    get_eway_sgstRate = fields.Float(string='SGST')
    get_eway_igstRate = fields.Float(string='IGST')
    get_eway_cessRate = fields.Float(string='CESS')
    get_eway_cessNonAdvol = fields.Float(string='CESS Non')
    get_eway_taxableAmount = fields.Float(string='taxable Amount')
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', 'Created By', default=lambda self: self.env.user)
    created_date = fields.Datetime(string='Created On', readonly=True, index=True, default=fields.Datetime.now)

