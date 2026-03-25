# models/auto_save_mixin.py
# Implementation of the Auto Save functionality.
from odoo import models, api, fields


class AutoSaveMixin(models.AbstractModel):
    _name = 'auto.save.mixin'
    _description = 'Auto Save Mixin'

    auto_save_trigger = fields.Boolean(compute='_compute_auto_save_trigger', store=True)

    @api.depends('field1', 'field2')  # Specify fields that should trigger auto-save
    def _compute_auto_save_trigger(self):
        for record in self:
            record.auto_save_trigger = True  # Set to True to trigger save

    @api.model
    def create(self, vals):
        record = super(AutoSaveMixin, self).create(vals)
        record._auto_save_record()
        return record

    def write(self, vals):
        res = super(AutoSaveMixin, self).write(vals)
        self._auto_save_record()
        return res

    def _auto_save_record(self):
        """Custom logic to auto-save the record."""
        for record in self:
            if record.auto_save_trigger:
                record.with_context(auto_save=True).write({})


# Extend this mixin to models globally.
class ResPartner(models.Model):
    _inherit = ['res.partner', 'auto.save.mixin']


class saleOrder(models.Model):
    _inherit = ['sale.order', 'auto.save.mixin']


class productProduct(models.Model):
    _inherit = ['product.product', 'auto.save.mixin']
