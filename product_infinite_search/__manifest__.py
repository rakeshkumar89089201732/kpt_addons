# -*- coding: utf-8 -*-
{
    'name': 'Product Infinite Search (Tally-style)',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Search products by any name, pattern, and word order (Tally-style) with high result limit',
    'description': """
Product Infinite Search
======================
* Search products by **any name** and **pattern** (partial match).
* **Order-independent search** (Tally-style): type words in any order;
  e.g. "tally erp" finds "ERP Tally" or "Tally Software".
* **Infinite search**: returns many more results (no low cap) so you can
  find products without being limited to the first few matches.
    """,
    'author': 'KPT',
    'depends': ['web', 'product'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'product_infinite_search/static/src/js/autocomplete_dropdown_sidebar.js',
            'product_infinite_search/static/src/js/record_autocomplete_more_results.js',
            'product_infinite_search/static/src/js/many2one_more_results.js',
            'product_infinite_search/static/src/js/tally_search_fallback.js',
            'product_infinite_search/static/src/scss/product_search_dropdown.scss',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
