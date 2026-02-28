from odoo import api, models
from odoo.tools.misc import formatLang


class ReportTDSDetails(models.AbstractModel):
    _name = 'report.hr_contract_extension.report_tds_details'
    _description = 'TDS Details Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['hr.tds'].browse(docids)

        def _format_lang(value, digits=2):
            return formatLang(self.env, value or 0.0, digits=digits)

        def _salary_income_display(rec):
            salary_total = float(getattr(rec, 'annual_salary', 0.0) or 0.0)
            addons_total = 0.0
            fy_start = getattr(rec, 'tds_from_date', False)
            fy_end = getattr(rec, 'tds_to_date', False)
            incs = getattr(rec, 'salary_increment_ids', self.env['salary.increment.line'])
            if incs and fy_start and fy_end:
                one_time_lines = incs.filtered(
                    lambda l: l.line_type == 'one_time'
                    and l.effective_from
                    and l.effective_from >= fy_start
                    and l.effective_from <= fy_end
                )
                addons_total = float(sum(one_time_lines.mapped('one_time_amount')) or 0.0)

            base_total = max(salary_total - addons_total, 0.0)
            if addons_total:
                return f"{_format_lang(base_total, digits=2)} + {_format_lang(addons_total, digits=2)}"
            return _format_lang(salary_total, digits=2)

        def _salary_base_amount(rec):
            salary_total = float(getattr(rec, 'annual_salary', 0.0) or 0.0)
            addons_total = 0.0
            fy_start = getattr(rec, 'tds_from_date', False)
            fy_end = getattr(rec, 'tds_to_date', False)
            incs = getattr(rec, 'salary_increment_ids', self.env['salary.increment.line'])
            if incs and fy_start and fy_end:
                one_time_lines = incs.filtered(
                    lambda l: l.line_type == 'one_time'
                    and l.effective_from
                    and l.effective_from >= fy_start
                    and l.effective_from <= fy_end
                )
                addons_total = float(sum(one_time_lines.mapped('one_time_amount')) or 0.0)
            return max(salary_total - addons_total, 0.0)

        def _one_time_incentive_rows(rec):
            rows = []
            fy_start = getattr(rec, 'tds_from_date', False)
            fy_end = getattr(rec, 'tds_to_date', False)
            incs = getattr(rec, 'salary_increment_ids', self.env['salary.increment.line'])
            if not (incs and fy_start and fy_end):
                return rows

            one_time_lines = incs.filtered(
                lambda l: l.line_type == 'one_time'
                and l.effective_from
                and l.effective_from >= fy_start
                and l.effective_from <= fy_end
                and (l.one_time_amount or 0.0)
            ).sorted(lambda l: l.effective_from)

            for l in one_time_lines:
                rows.append({
                    'date': l.effective_from,
                    'amount': float(l.one_time_amount or 0.0),
                    'reason': getattr(l, 'reason', False) or '',
                })
            return rows

        return {
            'doc_ids': docids,
            'doc_model': 'hr.tds',
            'docs': docs,
            'formatLang': _format_lang,
            'salary_income_display': _salary_income_display,
            'salary_base_amount': _salary_base_amount,
            'one_time_incentive_rows': _one_time_incentive_rows,
        }
