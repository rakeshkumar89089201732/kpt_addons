{
    "name": "KPT Frontdesk Reception",
    "summary": "Animated frontdesk welcome with selfie check-in",
    "version": "17.0.1.0.0",
    "category": "Human Resources/Frontdesk",
    "author": "KPT",
    "license": "LGPL-3",
    "depends": ["frontdesk"],
    "data": [
        "views/frontdesk_frontdesk_views.xml",
        "views/frontdesk_visitor_views.xml",
    ],
    "assets": {
        "frontdesk.assets_frontdesk": [
            "kpt_frontdesk_reception/static/src/js/frontdesk_reception_patch.js",
            "kpt_frontdesk_reception/static/src/xml/frontdesk_reception_templates.xml",
            "kpt_frontdesk_reception/static/src/scss/frontdesk_reception.scss",
        ],
    },
    "installable": True,
    "application": False,
}
