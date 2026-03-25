# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountAccount(models.Model):
    _inherit = 'account.account'

    account_type = fields.Selection(
        selection_add=[
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
        ondelete={
            'asset_deferred_current': 'cascade',
            'asset_deferred_non_current': 'cascade',
            'liability_deferred_current': 'cascade',
            'liability_deferred_non_current': 'cascade',
            'liability_provision': 'cascade',
            'asset_impairment': 'cascade',
            'equity_retained': 'cascade',
            'off_balance_commitment': 'cascade',
            'asset_inventory_lifo': 'cascade',
            'asset_development': 'cascade',
            'asset_prepaid_expenses': 'cascade',
            'liability_accrued_expenses': 'cascade',
        }
    )

    user_type_id = fields.Many2one('global.account.type', string='Account Type (Custom)')

    @api.onchange('user_type_id')
    def _onchange_user_type_id(self):
        if self.user_type_id:
            self.account_type = self.user_type_id.base_type

    @api.onchange('account_type')
    def _onchange_account_type(self):
        # Reverse sync: if user changes the base type directly (if visible) or system sets it, 
        # try to find a matching custom type if the current one doesn't match
        if self.account_type and (not self.user_type_id or self.user_type_id.base_type != self.account_type):
            pass

    def create(self, vals):
        if 'user_type_id' in vals and vals['user_type_id']:
            user_type = self.env['global.account.type'].browse(vals['user_type_id'])
            vals['account_type'] = user_type.base_type
        return super(AccountAccount, self).create(vals)

    def write(self, vals):
        if 'user_type_id' in vals:
            if vals['user_type_id']:
                user_type = self.env['global.account.type'].browse(vals['user_type_id'])
                vals['account_type'] = user_type.base_type
        return super(AccountAccount, self).write(vals)

