# -*- coding: utf-8 -*-

from odoo import models, fields

class GlobalAccountType(models.Model):
    _name = 'global.account.type'
    _description = 'Global Account Type'
    _order = 'category_id, name'

    name = fields.Char(string='Account Type', required=True, translate=True)
    category_id = fields.Many2one('global.account.category', string='Category', required=True)
    
    # We use the standard selection from account.account to map our custom types
    # This ensures reporting works correctly
    base_type = fields.Selection(
        selection=[
            ('asset_receivable', 'Receivable'),
            ('asset_cash', 'Bank and Cash'),
            ('asset_current', 'Current Assets'),
            ('asset_non_current', 'Non-current Assets'),
            ('asset_prepayments', 'Prepayments'),
            ('asset_fixed', 'Fixed Assets'),
            ('liability_payable', 'Payable'),
            ('liability_credit_card', 'Credit Card'),
            ('liability_current', 'Current Liabilities'),
            ('liability_non_current', 'Non-current Liabilities'),
            ('equity', 'Equity'),
            ('equity_unaffected', 'Current Year Earnings'),
            ('income', 'Income'),
            ('income_other', 'Other Income'),
            ('expense', 'Expenses'),
            ('expense_depreciation', 'Depreciation'),
            ('expense_direct_cost', 'Cost of Revenue'),
            ('off_balance', 'Off-Balance Sheet'),
            # Advanced Types
            ('asset_deferred_current', 'Current Deferred Assets'),
            ('asset_deferred_non_current', 'Non-Current Deferred Assets'),
            ('liability_deferred_current', 'Current Deferred Revenue'),
            ('liability_deferred_non_current', 'Non-Current Deferred Revenue'),
            ('liability_provision', 'Provisions'),
            ('asset_impairment', 'Asset Impairment Allowance'),
            ('equity_retained', 'Retained Earnings'),
            ('off_balance_commitment', 'Off-Balance Sheet Commitments'),
            ('asset_inventory_lifo', 'Inventory (LIFO)'),
            ('asset_development', 'Capitalized Development Costs'),
            ('asset_prepaid_expenses', 'Prepaid Expenses'),
            ('liability_accrued_expenses', 'Accrued Expenses'),
        ],
        string='Base Type',
        required=True,
        help="The standard Odoo account type this custom type maps to for reporting purposes."
    )
