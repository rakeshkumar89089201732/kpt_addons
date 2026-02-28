from odoo import models


class KpiProvider(models.AbstractModel):
    """Abstract model for providing KPI summary data.
    
    This module ensures kpi.provider exists in the registry even if digest module
    is not installed. If digest is installed, this will inherit from it.
    """
    _name = 'kpi.provider'
    _description = 'KPI Provider'

    def get_kpi_summary(self):
        """Return a list of KPI items for digest/summary views.
        
        Each item is a dict with keys: 'id', 'name', 'type', 'value'.
        Override in inheriting models to add more KPIs.
        """
        return []
