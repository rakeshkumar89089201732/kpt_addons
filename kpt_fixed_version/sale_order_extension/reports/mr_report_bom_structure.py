from odoo import api, fields, models, _

class ReportBomStructure(models.AbstractModel):
    _inherit = 'report.mrp.report_bom_structure'

    @api.model
    def _get_operation_cost(self, duration, operation):
        return (duration / 60.0) * (operation.workcenter_id.costs_hour + operation.workcenter_id.man_power_cost_hour + operation.workcenter_id.raw_material_cost_hour + operation.workcenter_id.additional_cost_hour)


