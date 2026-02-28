from odoo import fields, models ,api
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
from odoo.tools.misc import formatLang

class GrossPurchaseReport(models.TransientModel):
    _name = 'gross.purchase.report'

    date_from = fields.Date(default=date(date.today().year - 1, 4, 1))  # April 1st
    date_to = fields.Date(default=date(date.today().year, 3, 31))



    def generate_report(self):

        result = []
        months = self._get_month_ranges(self.date_from, self.date_to)
        totals = {'debit': 0, 'credit': 0, 'closing': 0}
        for month in months:
            customer_invoice_ids = self.env['account.move'].search([
                ('date', '>=', month['start']),
                ('date', '<=', month['end']),
                ('move_type', '=', 'out_invoice'),
                ('debit_origin_id', '=', False),
                ('state', '=', 'posted')
            ])
            customer_credit_note_ids = self.env['account.move'].search([
                ('invoice_date', '>=', month['start']),
                ('invoice_date', '<=', month['end']),
                ('move_type', '=', 'out_refund'),
                ('debit_origin_id', '!=', False),
                ('state', '=', 'posted')
            ])
            credit = sum(customer_invoice_ids.mapped('amount_total'))
            debit = sum(customer_credit_note_ids.mapped('amount_total'))
            closing = totals.get('closing') + abs(debit - credit)

            result.append({
                'month': month['name'],
                'debit': debit,
                'credit': credit,
                'closing': abs(closing),
                'closing_type': 'Cr'
            })

            totals['debit'] += debit
            totals['credit'] += credit
            totals['closing'] = abs(closing)

        return self.env.ref('sale_order_extension.gross_purchase_summary_pdf').report_action(self, data={'result': result, 'totals': totals, 'date_from': self.date_from, 'date_to': self.date_to}, config=False)


    def _get_month_ranges(self, start_date, end_date):
        months = []
        current = start_date
        while current <= end_date:
            start = current.replace(day=1)
            end = (start + relativedelta(months=1)) - timedelta(days=1)
            months.append({
                'start': start,
                'end': end,
                'name': start.strftime('%B')
            })
            current = start + relativedelta(months=1)
        return months

class GrossPurchaseSummaryReport(models.AbstractModel):
    _name = 'report.sale_order_extension.report_gross_purchase'

    def format_indian_number(self, amount):
        return formatLang(self.env, amount, grouping=True, monetary=False)

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': self._name,
            'data': data['result'],
            'totals': data['totals'],
            'date_from': datetime.strptime(data.get('date_from'), '%Y-%m-%d').date(),
            'date_to': datetime.strptime(data.get('date_to'), '%Y-%m-%d').date(),
            'currency': self.env.user.company_id.currency_id,
            'format_indian_number': self.format_indian_number,
        }


