from setuptools.unicode_utils import filesys_decode

from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = "stock.picking"

    amount_untaxed = fields.Monetary(string="Untaxed Amount", store=True, compute='_compute_amounts', tracking=5)
    amount_tax = fields.Monetary(string="Taxes", store=True, compute='_compute_amounts')
    amount_total = fields.Monetary(string="Total", store=True, compute='_compute_amounts', tracking=4)
    currency_id = fields.Many2one(
        compute='_compute_currency_id',
        store=True,
        comodel_name='res.currency',
        ondelete='restrict'
    )
    tax_totals = fields.Binary(compute='_compute_tax_totals', exportable=False)
    note = fields.Text()
    amount_total_rounded = fields.Float(
        string="Rounded Total",
        compute="_compute_price_total_rounded",
        store=True,
        help="Price Total rounded to the nearest integer."
    )

    amount_total_difference = fields.Float(
        string="Rounding Difference",
        compute="_compute_price_total_difference",
        store=True,
        help="Difference between the rounded price total and the original price total."
    )
    delivery_ref = fields.Char(string='Delivery Reference ')


    # # Below Fields are extra fields to compute
    # sgst_per  = fields.Char("")
    # sgst_amount = fields.Float(string="SGST", compute='action_compute_tax_amount', digits=(16, 2))
    # cgst_amount = fields.Float(string="CGST", compute='action_compute_tax_amount', digits=(16, 2))
    # igst_amount = fields.Float(string="IGST", compute='action_compute_tax_amount', digits=(16, 2))
    # cess_amt = fields.Float(string="CESS", compute='action_compute_tax_amount', digits=(16, 2))
    # cess_non = fields.Float(string="CESS_NON_ADVOL", compute='action_compute_tax_amount', digits=(16, 2))
    # other_amt = fields.Float(string='Others', compute='action_compute_tax_amount', digits=(16, 2))
    # amount_total_vals = fields.Float(string='amount_total_vals', store=True, compute='compute_total_vals',
    #                                  digits=(16, 2))
    # amount_untaxed_vals = fields.Float(string='amount_untaxed_vals', store=True, compute='compute_total_vals',
    #                                    digits=(16, 2))
    #
    # @api.depends('move_ids_without_package.tax_id', 'move_ids_without_package.price_unit', 'amount_total', 'amount_untaxed',
    #              'currency_id')
    # def action_compute_tax_amount(self):
    #     for picking in self:
    #         tax_details = {
    #             'SGST': 0.0,
    #             'CGST': 0.0,
    #             'IGST': 0.0,
    #             'CESS': 0.0,
    #             'CESS_NON_ADVOL': 0.0,
    #             'Others': 0.0
    #         }
    #         for line in picking.move_ids_without_package:
    #             tax_lines = line.tax_ids.compute_all(line.price_unit * line.quantity, currency=line.currency_id,
    #                                                  partner=line.partner_id)['taxes']
    #
    #             for tax_line in tax_lines:
    #                 tax_id = tax_line.get('id')
    #                 tax_amount = tax_line.get('amount', 0.0)
    #                 tax = self.env['account.tax'].browse(tax_id)
    #                 if tax and tax.name:
    #                     if 'SGST' in tax.name:
    #                         tax_details['SGST'] += tax_amount
    #                     elif 'CGST' in tax.name:
    #                         tax_details['CGST'] += tax_amount
    #                     elif 'IGST' in tax.name:
    #                         tax_details['IGST'] += tax_amount
    #                     elif 'CESS' in tax.name:
    #                         if tax.amount_type != "percent":
    #                             tax_details['CESS_NON_ADVOL'] += tax_amount
    #                         else:
    #                             tax_details['CESS'] += tax_amount
    #                     else:
    #                         tax_details['Others'] += tax_amount
    #         picking.update({
    #             'sgst_amount': tax_details['SGST'],
    #             'cgst_amount': tax_details['CGST'],
    #             'igst_amount': tax_details['IGST'],
    #             'cess_amt': tax_details['CESS'],
    #             'cess_non': tax_details['CESS_NON_ADVOL'],
    #             'other_amt': tax_details['Others'],
    #         })
    #
    # @api.depends('amount_total', 'amount_untaxed')
    # def compute_total_vals(self):
    #     for rec in self:
    #         rec.amount_total_vals = rec.amount_total
    #         rec.amount_untaxed_vals = rec.amount_untaxed

    @api.depends('amount_total')
    def _compute_price_total_rounded(self):
        """Compute the rounded value of the price_total field."""
        for picking in self:
            picking.amount_total_rounded = round(picking.amount_total) if picking.amount_total else 0.0

    @api.depends('amount_total', 'amount_total_rounded')
    def _compute_price_total_difference(self):
        """Compute the difference between the rounded value and the original price_total."""
        for picking in self:
            picking.amount_total_difference = (picking.amount_total_rounded - picking.amount_total) if picking.amount_total else 0.0

    @api.depends('company_id')
    def _compute_currency_id(self):
        for picking in self:
            picking.currency_id = picking.company_id.currency_id
            
            
    @api.depends_context('lang')
    @api.depends('move_ids_without_package.tax_id', 'move_ids_without_package.price_unit', 'amount_total', 'amount_untaxed', 'currency_id')
    def _compute_tax_totals(self):
        for picking in self:
            picking = picking.with_company(picking.company_id)
            picking_lines = picking.move_ids_without_package
            picking.tax_totals = picking.env['account.tax']._prepare_tax_totals(
                [x._convert_to_tax_base_line_dict() for x in picking_lines],
                picking.currency_id or picking.company_id.currency_id,
            )


    @api.depends('move_ids_without_package.price_subtotal', 'move_ids_without_package.price_tax', 'move_ids_without_package.price_total')
    def _compute_amounts(self):
        """Compute the total amounts of the SO."""
        for picking in self:
            picking = picking.with_company(picking.company_id)
            picking_lines = picking.move_ids_without_package

            if picking.company_id.tax_calculation_rounding_method == 'round_globally':
                tax_results = picking.env['account.tax']._compute_taxes([
                    line._convert_to_tax_base_line_dict()
                    for line in picking_lines
                ])
                totals = tax_results['totals']
                amount_untaxed = totals.get(picking.currency_id, {}).get('amount_untaxed', 0.0)
                amount_tax = totals.get(picking.currency_id, {}).get('amount_tax', 0.0)
            else:
                amount_untaxed = sum(picking_lines.mapped('price_subtotal'))
                amount_tax = sum(picking_lines.mapped('price_tax'))

            picking.amount_untaxed = amount_untaxed
            picking.amount_tax = amount_tax
            picking.amount_total = picking.amount_untaxed + picking.amount_tax




