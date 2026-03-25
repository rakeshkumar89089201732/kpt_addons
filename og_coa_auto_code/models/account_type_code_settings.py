from odoo import models, fields, _, api
from odoo.exceptions import ValidationError

class AccountTypeCodeSettings(models.Model):
    _name = "account.type.code.settings"
    _description = "Account Type Code Settings"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "account_type desc"

    account_type = fields.Selection(
        selection=[
            ("asset_receivable", "Receivable"),
            ("asset_cash", "Bank and Cash"),
            ("asset_current", "Current Assets"),
            ("asset_non_current", "Non-current Assets"),
            ("asset_prepayments", "Prepayments"),
            ("asset_fixed", "Fixed Assets"),
            ("liability_payable", "Payable"),
            ("liability_credit_card", "Credit Card"),
            ("liability_current", "Current Liabilities"),
            ("liability_non_current", "Non-current Liabilities"),
            ("equity", "Equity"),
            ("equity_unaffected", "Current Year Earnings"),
            ("income", "Income"),
            ("income_other", "Other Income"),
            ("expense", "Expenses"),
            ("expense_depreciation", "Depreciation"),
            ("expense_direct_cost", "Cost of Revenue"),
            ("off_balance", "Off-Balance Sheet"),
        ],
        string="Account Type", tracking=True,
        required=True,
        compute='_compute_account_type', store=True, readonly=False, precompute=True,
        help="Account Type is used for information purpose, to generate country-specific legal reports, and set the rules to close a fiscal year and generate opening entries."
    )

    code_from = fields.Char(size=64, required=True, tracking=True, index=True, unaccent=False)

    @api.constrains('account_type', 'code_from')
    def _check_unique_constraint_account_type_code_from(self):
        for rec in self:
            msg1 = "Account Type `%s`" % (rec.account_type)
            msg2 = "Code From `%s`" % (rec.code_from)
            envObj = self.env['account.type.code.settings']

            conditionList1 = [('id', '!=', rec.id),('account_type', '=ilike', str(rec.account_type))]
            conditionList2 = [('id', '!=', rec.id),('code_from', '=', str(rec.code_from))]

            records1 = envObj.search(conditionList1, limit=1)
            if records1:
                raise ValidationError("'" + msg1 + "' already exists!")

            records2 = envObj.search(conditionList2, limit=1)
            if records2:
                raise ValidationError("'" + msg2 + "' already exists!")
