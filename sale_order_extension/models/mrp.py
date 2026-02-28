
from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    man_power_cost = fields.Float('Man power cost', default=0.0, compute='_compute_total_mo_cost', store=True)
    raw_material_cost = fields.Float('Raw material cost', default=0.0, compute='_compute_total_mo_cost', store=True)
    additional_cost = fields.Float('Additional cost', default=0.0, compute='_compute_total_mo_cost', store=True)

    @api.depends('workorder_ids.man_power_cost_hour', 'workorder_ids.raw_material_cost_hour', 'workorder_ids.additional_cost_hour',
                 'workorder_ids.workcenter_id.man_power_cost_hour', 'workorder_ids.workcenter_id.man_power_cost_hour')
    def _compute_total_mo_cost(self):
        for mo in self:
            if mo.workorder_ids:
                man_power_cost = 0.0
                raw_material_cost = 0.0
                additional_cost = 0.0
                for wo in mo.workorder_ids:
                    duration = (wo.duration_expected / 60) * wo.qty_remaining
                    man_power_cost += duration * (wo.man_power_cost_hour or wo.workcenter_id.man_power_cost_hour)
                    raw_material_cost += duration * (wo.raw_material_cost_hour or wo.workcenter_id.raw_material_cost_hour)
                    additional_cost += duration * (wo.additional_cost_hour or wo.workcenter_id.additional_cost_hour)
                mo.man_power_cost = man_power_cost
                mo.raw_material_cost = raw_material_cost
                mo.additional_cost = additional_cost
            else:
                mo.man_power_cost = 0.0
                mo.raw_material_cost = 0.0
                mo.additional_cost = 0.0


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    man_power_cost_hour = fields.Float('Man power cost', default=0.0)
    raw_material_cost_hour = fields.Float('Raw material cost', default=0.0)
    additional_cost_hour = fields.Float('Additional cost', default=0.0)



class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    man_power_cost_hour = fields.Float('Man power cost', default=0.0)
    raw_material_cost_hour = fields.Float('Raw material cost', default=0.0)
    additional_cost_hour = fields.Float('Additional cost', default=0.0)


    def _cal_cost(self):
        total = 0
        for wo in self:
            duration = sum(wo.time_ids.mapped('duration'))
            total += (duration / 60.0) * (wo.workcenter_id.costs_hour + wo.workcenter_id.man_power_cost_hour + wo.workcenter_id.raw_material_cost_hour + wo.workcenter_id.additional_cost_hour)
        return total


    def button_finish(self):
        date_finished = fields.Datetime.now()
        for workorder in self:
            if workorder.state in ('done', 'cancel'):
                continue
            workorder.end_all()
            vals = {
                'qty_produced': workorder.qty_produced or workorder.qty_producing or workorder.qty_production,
                'state': 'done',
                'date_finished': date_finished,
                'costs_hour': workorder.workcenter_id.costs_hour,
                'man_power_cost_hour': workorder.workcenter_id.man_power_cost_hour,
                'raw_material_cost_hour': workorder.workcenter_id.raw_material_cost_hour,
                'additional_cost_hour': workorder.workcenter_id.additional_cost_hour
            }
            if not workorder.date_start or date_finished < workorder.date_start:
                vals['date_start'] = date_finished
            workorder.with_context(bypass_duration_calculation=True).write(vals)
        return True


    def button_done(self):
        if any(x.state in ('done', 'cancel') for x in self):
            raise UserError(_('A Manufacturing Order is already done or cancelled.'))
        self.end_all()
        end_date = datetime.now()
        return self.write({
            'state': 'done',
            'date_finished': end_date,
            'costs_hour': self.workcenter_id.costs_hour,
            'man_power_cost_hour': self.workcenter_id.man_power_cost_hour,
            'raw_material_cost_hour': self.workcenter_id.raw_material_cost_hour,
            'additional_cost_hour': self.workcenter_id.additional_cost_hour
        })



    def _compute_expected_operation_cost(self):
        return (self.duration_expected / 60.0) * ((self.costs_hour or self.workcenter_id.costs_hour) + (self.man_power_cost_hour or self.workcenter_id.man_power_cost_hour) + (self.raw_material_cost_hour or self.workcenter_id.raw_material_cost_hour) + (self.additional_cost_hour or self.workcenter_id.additional_cost_hour))

    def _compute_current_operation_cost(self):
        return (self.get_duration() / 60.0) * ((self.costs_hour or self.workcenter_id.costs_hour) + (self.man_power_cost_hour or self.workcenter_id.man_power_cost_hour) + (self.raw_material_cost_hour or self.workcenter_id.raw_material_cost_hour) + (self.additional_cost_hour or self.workcenter_id.additional_cost_hour))



class MrpRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    def _total_cost_per_hour(self):
        self.ensure_one()
        return self.workcenter_id.costs_hour + self.workcenter_id.man_power_cost_hour + self.workcenter_id.raw_material_cost_hour + self.workcenter_id.additional_cost_hour