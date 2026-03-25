from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    allow_other_company_bill = fields.Boolean(
        string='Allow Other Company (Bill)',
        default=False,
        help='Enable to select billing address from companies not related to the selected customer',
    )
    allow_other_company_ship = fields.Boolean(
        string='Allow Other Company (Ship)',
        default=False,
        help='Enable to select shipping address from companies not related to the selected customer',
    )
    
    bill_to_contact_id = fields.Many2one(
        'res.partner',
        string='Bill To',
        help='Select billing contact from the customer or its contacts',
    )
    ship_to_contact_id = fields.Many2one(
        'res.partner',
        string='Ship To',
        help='Select shipping contact from the customer or its contacts',
    )

    @api.onchange('partner_id')
    def _onchange_partner_set_contacts(self):
        for order in self:
            # Default bill/ship to main partner when partner changes
            order.bill_to_contact_id = order.partner_id
            order.ship_to_contact_id = order.partner_id
            order.partner_invoice_id = order.partner_id
            order.partner_shipping_id = order.partner_id
            # Reset toggle flags when partner changes
            order.allow_other_company_bill = False
            order.allow_other_company_ship = False
    
    @api.onchange('allow_other_company_bill')
    def _onchange_allow_other_company_bill(self):
        # Reset bill_to when toggling to avoid invalid selection
        for order in self:
            if not order.allow_other_company_bill:
                # When disabling, reset to partner if current selection is not related
                if order.bill_to_contact_id and order.partner_id:
                    if (order.bill_to_contact_id.id != order.partner_id.id and 
                        order.bill_to_contact_id.commercial_partner_id.id != order.partner_id.commercial_partner_id.id):
                        order.bill_to_contact_id = order.partner_id
    
    @api.onchange('allow_other_company_ship')
    def _onchange_allow_other_company_ship(self):
        # Reset ship_to when toggling to avoid invalid selection
        for order in self:
            if not order.allow_other_company_ship:
                # When disabling, reset to partner if current selection is not related
                if order.ship_to_contact_id and order.partner_id:
                    if (order.ship_to_contact_id.id != order.partner_id.id and 
                        order.ship_to_contact_id.commercial_partner_id.id != order.partner_id.commercial_partner_id.id):
                        order.ship_to_contact_id = order.partner_id

    @api.onchange('bill_to_contact_id')
    def _onchange_bill_to_contact(self):
        for order in self:
            if order.bill_to_contact_id:
                order.partner_invoice_id = order.bill_to_contact_id

    @api.onchange('ship_to_contact_id')
    def _onchange_ship_to_contact(self):
        for order in self:
            if order.ship_to_contact_id:
                order.partner_shipping_id = order.ship_to_contact_id

    @api.model
    def create(self, vals):
        # When bill/ship selections provided, push to invoice/shipping partner
        if vals.get('bill_to_contact_id'):
            vals.setdefault('partner_invoice_id', vals['bill_to_contact_id'])
        if vals.get('ship_to_contact_id'):
            vals.setdefault('partner_shipping_id', vals['ship_to_contact_id'])
        return super().create(vals)

    def write(self, vals):
        res = super().write(vals)
        for order in self:
            if 'bill_to_contact_id' in vals and order.bill_to_contact_id:
                order.partner_invoice_id = order.bill_to_contact_id
            if 'ship_to_contact_id' in vals and order.ship_to_contact_id:
                order.partner_shipping_id = order.ship_to_contact_id
        return res
