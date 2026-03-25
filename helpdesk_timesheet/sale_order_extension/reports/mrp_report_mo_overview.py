from odoo import models, api, _

class ReportMoOverview(models.AbstractModel):
    _inherit = 'report.mrp.report_mo_overview'


    def _get_finished_operation_data(self, production, level=0, current_index=False):
        currency = (production.company_id or self.env.company).currency_id
        done_operation_uom = _("Hours")
        operations = []
        total_duration = total_duration_expected = total_cost = 0
        for index, workorder in enumerate(production.workorder_ids):
            hourly_cost = ((workorder.costs_hour or workorder.workcenter_id.costs_hour) + (workorder.man_power_cost_hour or  workorder.workcenter_id.man_power_cost_hour) + (workorder.raw_material_cost_hour or  workorder.workcenter_id.raw_material_cost_hour) + (workorder.additional_cost_hour or  workorder.workcenter_id.additional_cost_hour))
            duration = workorder.get_duration() / 60
            total_duration += duration
            total_duration_expected += workorder.duration_expected
            operation_cost = duration * hourly_cost
            total_cost += operation_cost
            operations.append({
                'level': level,
                'index': f"{current_index}W{index}",
                'name': f"{workorder.workcenter_id.display_name}: {workorder.display_name}",
                'quantity': duration,
                'uom_name': done_operation_uom,
                'uom_precision': 4,
                'unit_cost': hourly_cost,
                'mo_cost': currency.round(operation_cost),
                'real_cost': currency.round(operation_cost),
                'currency_id': currency.id,
                'currency': currency,
            })
        return {
            'summary': {
                'index': f"{current_index}W",
                'done': True,
                'quantity': total_duration,
                'quantity_decorator': self._get_comparison_decorator(total_duration_expected, total_duration, 0.01),
                'mo_cost': total_cost,
                'real_cost': total_cost,
                'uom_name': done_operation_uom,
                'currency_id': currency.id,
                'currency': currency,
            },
            'details': operations,
        }