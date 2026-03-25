# -*- coding: utf-8 -*-
{
    'name': 'Product Voice Search',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Voice-driven product search using existing infinite search logic',
    'description': """
Voice-based product search that reuses the Tally-style infinite search from product_infinite_search.
Click mic, speak your product keywords, and see matching products instantly.
""",
    'author': 'KPT',
    'depends': ['web', 'product', 'product_infinite_search', 'stock'],
    'data': [
        'views/product_voice_search_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'product_voice_search/static/src/css/voice_product_search.css',
            'product_voice_search/static/src/xml/voice_product_search.xml',
            'product_voice_search/static/src/js/voice_product_search.js',
            'product_voice_search/static/src/js/voice_product_m2o.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
