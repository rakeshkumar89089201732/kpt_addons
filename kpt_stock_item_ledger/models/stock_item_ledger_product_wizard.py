from odoo import api, fields, models, _


class StockItemLedgerProductWizard(models.TransientModel):
    _name = 'stock.item.ledger.product.wizard'
    _description = 'Stock Item Ledger Product Selection'

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain="[('type', 'in', ['product', 'consu'])]",
    )
    report_id = fields.Many2one(
        'account.report',
        string='Report',
        required=True,
    )

    def action_apply_product(self):
        self.ensure_one()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'account_report',
            'context': {
                'report_id': self.report_id.id,
                'kpt_product_id': self.product_id.id,
                'kpt_product_name': self.product_id.display_name,
            },
        }
