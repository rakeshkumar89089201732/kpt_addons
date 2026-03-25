# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductPackaging(models.Model):
    """
    Extends product.packaging to add detailed weight and packaging information.
    
    This extension adds fields for tracking:
    - Weight per individual piece
    - Number of pieces per packaging
    - Weight of empty packaging
    - Calculated average weight per packaging
    """
    _inherit = 'product.packaging'

    # Weight per individual piece (Wt./Pcs)
    weight_per_piece = fields.Float(
        string='Weight per Piece',
        digits='Stock Weight',
        help="Weight of one individual piece/unit in this packaging"
    )

    # Number of pieces in this packaging (PCS/Bag)
    pieces_per_packaging = fields.Integer(
        string='Pieces per Packaging',
        default=1,
        help="Number of pieces contained in this packaging unit (e.g., pieces per bag)"
    )

    # Weight of empty packaging material
    packaging_weight = fields.Float(
        string='Packaging Weight',
        digits='Stock Weight',
        default=0.0,
        help="Weight of the empty packaging material (bag, box, etc.)"
    )

    # Calculated average weight per packaging (AVG Wt./Bag)
    avg_weight_per_packaging = fields.Float(
        string='Avg Weight per Packaging',
        compute='_compute_avg_weight_per_packaging',
        store=True,
        digits='Stock Weight',
        help="Calculated average weight per packaging (Weight per Piece × Pieces per Packaging + Packaging Weight)"
    )

    @api.depends('weight_per_piece', 'pieces_per_packaging', 'packaging_weight')
    def _compute_avg_weight_per_packaging(self):
        """
        Compute the average weight per packaging.
        
        Formula: (Weight per Piece × Pieces per Packaging) + Packaging Weight
        
        This gives the total weight of a full packaging including:
        - The weight of all pieces inside
        - The weight of the packaging material itself
        """
        for packaging in self:
            # Calculate total weight of pieces
            pieces_weight = (packaging.weight_per_piece or 0.0) * (packaging.pieces_per_packaging or 0)
            
            # Add packaging material weight
            packaging.avg_weight_per_packaging = pieces_weight + (packaging.packaging_weight or 0.0)

    @api.constrains('weight_per_piece', 'pieces_per_packaging', 'packaging_weight')
    def _check_positive_values(self):
        """
        Ensure that weight and piece values are non-negative.
        
        Following Odoo best practices for data validation.
        """
        for packaging in self:
            if packaging.weight_per_piece and packaging.weight_per_piece < 0:
                raise ValidationError(_('Weight per piece must be a positive value.'))
            
            if packaging.pieces_per_packaging and packaging.pieces_per_packaging < 0:
                raise ValidationError(_('Pieces per packaging must be a positive value.'))
            
            if packaging.packaging_weight and packaging.packaging_weight < 0:
                raise ValidationError(_('Packaging weight must be a positive value.'))
