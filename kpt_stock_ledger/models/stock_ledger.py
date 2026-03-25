from odoo import api, fields, models, _
from odoo.tools import float_round


class StockLedger(models.Model):
    _name = 'stock.ledger'
    _description = 'Stock Ledger'
    _order = 'date, id'
    _rec_name = 'product_id'

    date = fields.Date(
        string='Date',
        required=True,
        index=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        index=True,
    )
    particulars = fields.Char(
        string='Particulars',
        help='Partner name or description',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
    )
    vch_type = fields.Selection([
        ('opening', 'Opening Balance'),
        ('sales', 'Sales'),
        ('purchase', 'Purchase'),
        ('sales_return', 'Sales Return'),
        ('purchase_return', 'Purchase Return'),
        ('stock_journal', 'Stock Journal'),
        ('manufacturing', 'Manufacturing'),
        ('adjustment', 'Inventory Adjustment'),
        ('internal', 'Internal Transfer'),
        ('delivery', 'Delivery Order'),
        ('receipt', 'Receipt'),
    ], string='Vch Type', default='stock_journal')
    vch_no = fields.Char(
        string='Vch No',
        help='Voucher/Document Number',
    )
    reference = fields.Char(
        string='Reference',
    )
    
    # Inwards
    inward_qty = fields.Float(
        string='Inward Quantity',
        digits='Product Unit of Measure',
        default=0.0,
    )
    inward_value = fields.Float(
        string='Inward Value',
        digits='Product Price',
        default=0.0,
    )
    inward_rate = fields.Float(
        string='Inward Rate',
        compute='_compute_rates',
        store=True,
        digits='Product Price',
    )
    
    # Outwards
    outward_qty = fields.Float(
        string='Outward Quantity',
        digits='Product Unit of Measure',
        default=0.0,
    )
    outward_value = fields.Float(
        string='Outward Value',
        digits='Product Price',
        default=0.0,
    )
    outward_rate = fields.Float(
        string='Outward Rate',
        compute='_compute_rates',
        store=True,
        digits='Product Price',
    )
    
    # Closing
    closing_qty = fields.Float(
        string='Closing Quantity',
        digits='Product Unit of Measure',
        default=0.0,
    )
    closing_value = fields.Float(
        string='Closing Value',
        digits='Product Price',
        default=0.0,
    )
    closing_rate = fields.Float(
        string='Closing Rate',
        compute='_compute_rates',
        store=True,
        digits='Product Price',
    )
    
    uom_id = fields.Many2one(
        'uom.uom',
        string='UoM',
        related='product_id.uom_id',
        store=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )
    stock_move_id = fields.Many2one(
        'stock.move',
        string='Stock Move',
        ondelete='cascade',
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
    )
    location_dest_id = fields.Many2one(
        'stock.location',
        string='Destination Location',
    )
    
    @api.depends('inward_qty', 'inward_value', 'outward_qty', 'outward_value', 'closing_qty', 'closing_value')
    def _compute_rates(self):
        for record in self:
            # Inward rate
            if record.inward_qty and record.inward_qty != 0:
                record.inward_rate = record.inward_value / record.inward_qty
            else:
                record.inward_rate = 0.0
            
            # Outward rate
            if record.outward_qty and record.outward_qty != 0:
                record.outward_rate = record.outward_value / record.outward_qty
            else:
                record.outward_rate = 0.0
            
            # Closing rate
            if record.closing_qty and record.closing_qty != 0:
                record.closing_rate = record.closing_value / record.closing_qty
            else:
                record.closing_rate = 0.0
