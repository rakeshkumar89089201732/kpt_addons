from odoo import models, fields
from odoo.exceptions import ValidationError


class TaxSlabHelpLink(models.Model):
    _name = 'tax.slab.help.link'
    _description = 'Tax Slab Help Link'
    _order = 'sequence, id'

    tax_slab_id = fields.Many2one('tax.slab', string='Tax Slab', required=True, ondelete='cascade')
    name = fields.Char(string='Title', required=True)
    url = fields.Char(string='URL', required=True)
    sequence = fields.Integer(default=10)

    def action_open_url(self):
        self.ensure_one()
        if not self.url:
            raise ValidationError('Please set URL first.')
        return {
            'type': 'ir.actions.act_url',
            'url': self.url,
            'target': 'new',
        }
