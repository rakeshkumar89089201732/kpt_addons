from odoo import api, fields, models, tools


class StockLedgerReport(models.Model):
    _name = 'stock.ledger.report'
    _description = 'Stock Ledger Report'
    _auto = False
    _order = 'product_id, date, id'

    date = fields.Date(string='Date', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', readonly=True)
    particulars = fields.Char(string='Particulars', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    vch_type = fields.Char(string='Vch Type', readonly=True)
    vch_no = fields.Char(string='Vch No', readonly=True)
    reference = fields.Char(string='Reference', readonly=True)
    
    inward_qty = fields.Float(string='Inward Qty', readonly=True, digits='Product Unit of Measure')
    inward_value = fields.Float(string='Inward Value', readonly=True, digits='Product Price')
    outward_qty = fields.Float(string='Outward Qty', readonly=True, digits='Product Unit of Measure')
    outward_value = fields.Float(string='Outward Value', readonly=True, digits='Product Price')
    balance_qty = fields.Float(string='Balance Qty', readonly=True, digits='Product Unit of Measure')
    balance_value = fields.Float(string='Balance Value', readonly=True, digits='Product Price')
    
    uom_id = fields.Many2one('uom.uom', string='UoM', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    location_id = fields.Many2one('stock.location', string='Source Location', readonly=True)
    location_dest_id = fields.Many2one('stock.location', string='Dest Location', readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Picking', readonly=True)
    stock_move_id = fields.Many2one('stock.move', string='Stock Move', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = """
            CREATE OR REPLACE VIEW %s AS (
                WITH stock_movements AS (
                    SELECT 
                        sm.id as id,
                        sm.date::date as date,
                        sm.product_id,
                        pt.id as product_tmpl_id,
                        COALESCE(
                            rp.name,
                            sp.name,
                            sm.reference,
                            sm.name
                        ) as particulars,
                        COALESCE(sm.partner_id, sp.partner_id) as partner_id,
                        CASE 
                            WHEN sp.picking_type_id IS NOT NULL THEN
                                CASE spt.code
                                    WHEN 'incoming' THEN 
                                        CASE WHEN sp.origin LIKE '%%Return%%' THEN 'Purchase Return' ELSE 'Purchase' END
                                    WHEN 'outgoing' THEN 
                                        CASE WHEN sp.origin LIKE '%%Return%%' THEN 'Sales Return' ELSE 'Sales' END
                                    WHEN 'internal' THEN 'Internal Transfer'
                                    WHEN 'mrp_operation' THEN 'Manufacturing'
                                    ELSE 'Stock Journal'
                                END
                            ELSE 'Stock Journal'
                        END as vch_type,
                        COALESCE(sp.name, sm.reference) as vch_no,
                        sm.reference,
                        CASE 
                            WHEN sl_dest.usage = 'internal' AND sl_src.usage != 'internal' 
                            THEN sm.product_qty 
                            ELSE 0.0 
                        END as inward_qty,
                        CASE 
                            WHEN sl_dest.usage = 'internal' AND sl_src.usage != 'internal' 
                            THEN ABS(COALESCE((SELECT SUM(value) FROM stock_valuation_layer WHERE stock_move_id = sm.id), 0))
                            ELSE 0.0 
                        END as inward_value,
                        CASE 
                            WHEN sl_src.usage = 'internal' AND sl_dest.usage != 'internal' 
                            THEN sm.product_qty 
                            ELSE 0.0 
                        END as outward_qty,
                        CASE 
                            WHEN sl_src.usage = 'internal' AND sl_dest.usage != 'internal' 
                            THEN ABS(COALESCE((SELECT SUM(value) FROM stock_valuation_layer WHERE stock_move_id = sm.id), 0))
                            ELSE 0.0 
                        END as outward_value,
                        sm.product_uom as uom_id,
                        sm.company_id,
                        sm.location_id,
                        sm.location_dest_id,
                        sm.picking_id
                    FROM stock_move sm
                    LEFT JOIN stock_picking sp ON sm.picking_id = sp.id
                    LEFT JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
                    LEFT JOIN stock_location sl_src ON sm.location_id = sl_src.id
                    LEFT JOIN stock_location sl_dest ON sm.location_dest_id = sl_dest.id
                    LEFT JOIN product_product pp ON sm.product_id = pp.id
                    LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                    LEFT JOIN res_partner rp ON COALESCE(sm.partner_id, sp.partner_id) = rp.id
                    WHERE sm.state = 'done'
                        AND (sl_src.usage = 'internal' OR sl_dest.usage = 'internal')
                )
                SELECT 
                    id,
                    date,
                    product_id,
                    product_tmpl_id,
                    particulars,
                    partner_id,
                    vch_type,
                    vch_no,
                    reference,
                    inward_qty,
                    inward_value,
                    outward_qty,
                    outward_value,
                    SUM(inward_qty - outward_qty) OVER (PARTITION BY product_id ORDER BY date, id) as balance_qty,
                    SUM(inward_value - outward_value) OVER (PARTITION BY product_id ORDER BY date, id) as balance_value,
                    uom_id,
                    company_id,
                    location_id,
                    location_dest_id,
                    picking_id,
                    id as stock_move_id
                FROM stock_movements
                ORDER BY product_id, date, id
            )
        """ % self._table
        self.env.cr.execute(query)
