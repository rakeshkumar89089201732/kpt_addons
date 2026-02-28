from odoo import models, fields, api



class SaleOrderGSTAutomation(models.Model):
    _inherit = 'sale.order'

    @api.onchange('partner_id', 'order_line')
    def _apply_gst_taxes(self):
        """Automatically selects GST based on customer location"""
        for order in self:
            if order.partner_id and order.company_id:
                customer_state = order.partner_id.state_id
                company_state = order.company_id.state_id

                # Fetch tax records
                # cgst_sgst_tax = self.env['account.tax'].search([('name', 'ilike', 'CGST'), ('type_tax_use', '=', 'sale')], limit=1)
                # sgst_tax = self.env['account.tax'].search([('name', 'ilike', 'SGST'), ('type_tax_use', '=', 'sale')], limit=1)
                igst_tax = self.env['account.tax'].search([('tax_group_id.name', '=', 'IGST'), ('type_tax_use', '=', 'sale'), ('active', '=', True)], limit=1)
                gst_tax = self.env['account.tax'].search([('tax_group_id.name', '=', 'GST'), ('type_tax_use', '=', 'sale'), ('active', '=', True)], limit=1)


                # Apply tax based on state
                for line in order.order_line:
                    if line.product_template_id and line.product_template_id.taxes_id:
                        if customer_state == company_state:
                            line.tax_id = [(6, 0, [gst_tax.id])]
                        else:
                            line.tax_id = [(6, 0, [igst_tax.id])]
                    else:
                        line.tax_id = False




class PurchaseOrderGSTAutomation(models.Model):
    _inherit = 'purchase.order'

    @api.onchange('partner_id', 'order_line')
    def _apply_gst_taxes(self):
        """Automatically selects GST based on customer location"""
        for order in self:
            if order.partner_id and order.company_id:
                customer_state = order.partner_id.state_id
                company_state = order.company_id.state_id

                # Fetch tax records
                # cgst_sgst_tax = self.env['account.tax'].search([('name', 'ilike', 'CGST'), ('type_tax_use', '=', 'purchase')], limit=1)
                igst_tax = self.env['account.tax'].search([('tax_group_id.name', '=', 'IGST'), ('type_tax_use', '=', 'purchase'), ('active', '=', True)], limit=1)
                gst_tax = self.env['account.tax'].search([('tax_group_id.name', '=', 'GST'), ('type_tax_use', '=', 'purchase'), ('active', '=', True)], limit=1)


                # Apply tax based on state
                for line in order.order_line:
                    if line.product_id and line.product_id.supplier_taxes_id:
                        if customer_state == company_state:
                            line.taxes_id = [(6, 0, [gst_tax.id])]
                        else:
                            line.taxes_id = [(6, 0, [igst_tax.id])]
                    else:
                        line.taxes_id = False


class StockPickingGSTAutomation(models.Model):
    _inherit = 'stock.picking'

    @api.onchange('partner_id', 'move_ids_without_package')
    def _apply_gst_taxes(self):
        """Ensures GST tax is correctly applied in delivery orders"""
        for picking in self:
            if picking.partner_id and picking.company_id:
                customer_state = picking.partner_id.state_id
                company_state = picking.company_id.state_id

                # Fetch tax records
                # cgst_sgst_tax = self.env['account.tax'].search([
                #     ('name', 'ilike', 'CGST'),
                #     ('type_tax_use', 'in', ['sale', 'purchase'])
                # ])
                igst_tax = self.env['account.tax'].search([('tax_group_id.name', '=', 'IGST'), ('type_tax_use', 'in', ['purchase', 'sale']), ('active', '=', True)])
                gst_tax = self.env['account.tax'].search([('tax_group_id.name', '=', 'GST'), ('type_tax_use', 'in', ['purchase', 'sale']), ('active', '=', True)])
                for move in picking.move_ids_without_package:
                    if move.product_id and move.product_id.taxes_id and picking.picking_type_id.sequence_code == 'OUT':
                        igst_tax = igst_tax.filtered(lambda x: x.type_tax_use == 'sale')[:1]
                        gst_tax = gst_tax.filtered(lambda x: x.type_tax_use == 'sale')[:1]
                        if customer_state == company_state:
                            move.tax_id = [(6, 0, [gst_tax.id])]
                        else:
                            move.tax_id = [(6, 0, [igst_tax.id])]
                    elif move.product_id and move.product_id.supplier_taxes_id and picking.picking_type_id.sequence_code == 'IN':
                        igst_tax = igst_tax.filtered(lambda x: x.type_tax_use == 'purchase')[:1]
                        gst_tax = gst_tax.filtered(lambda x: x.type_tax_use == 'purchase')[:1]
                        if customer_state == company_state:
                            move.tax_id = [(6, 0, [gst_tax.id])]
                        else:
                            move.tax_id = [(6, 0, [igst_tax.id])]
                    else:
                        move.tax_id = False


class AccountMoveGSTAutomation(models.Model):
    _inherit = 'account.move'

    @api.onchange('partner_id')
    def _apply_gst_taxes(self):
        """Automatically selects GST based on vendor location"""
        for move in self:
            if move.partner_id and move.company_id:
                vendor_state = move.partner_id.state_id
                company_state = move.company_id.state_id

                igst_tax = self.env['account.tax'].search([('tax_group_id.name', '=', 'IGST'), ('type_tax_use', '=', 'purchase'), ('active', '=', True)], limit=1)
                gst_tax = self.env['account.tax'].search([('tax_group_id.name', '=', 'GST'), ('type_tax_use', '=', 'sale'), ('active', '=', True)], limit=1)

                tax_to_apply = gst_tax if vendor_state == company_state else igst_tax

                for line in move.invoice_line_ids:
                    if line.product_id and (line.product_id.taxes_id or line.product_id.supplier_taxes_id):
                        line.tax_ids = [(6, 0, tax_to_apply.ids)]
                    else:
                        line.tax_ids = False

