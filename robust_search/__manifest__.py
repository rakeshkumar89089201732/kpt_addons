# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Robust Product Search',
    'version': '17.0.2.3.0',
    'category': 'Sales/Sales',
    'summary': 'Enhanced product search with partial matching and fuzzy search capabilities',
    'description': """
        Robust Product Search
        =====================
        This module enhances the product search functionality across the entire Odoo system.
        
        Features:
        ---------
        * Search products by partial name matches (e.g., "pn 16 63" finds "Pnuemato 16MM")
        * Handles special characters: (), /, -, etc. (e.g., "pn (20mm)" works!)
        * Case-insensitive search (PN = pn = Pn)
        * Smart tokenization extracts meaningful search terms
        * Search by internal reference with partial matching
        * Split search terms and match individually
        * Works everywhere: product lists, sale orders, purchase orders, etc.
        * Maintains standard Odoo search performance
        
        Example Searches:
        ----------------
        - "pn 10 (20mm)" → finds products with "pn", "10", and "20mm" (handles parentheses)
        - "PC-02020" → finds products with "pc" and "02020" (handles dash)
        - "blue/yellow clamp" → finds products with "blue", "yellow", and "clamp"
        - "PN 16 BLUE" → same as "pn 16 blue" (case-insensitive)
        
        This module overrides the product search methods to provide a more intuitive
        search experience without requiring exact name or reference matches.
    """,
    'author': 'KPT',
    'website': 'https://www.kpt.com',
    'depends': ['product', 'sale_management', 'purchase'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
