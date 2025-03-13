# -*- coding: utf-8 -*-

{
    'name': 'Approval Workflow Advanced',
    'summary': 'Approval Workflow Advanced',
    'description': """
    Approval Workflow Advanced
""",
    'author': 'Cloud Open Technologies/K8 Team',
    'website': 'https://on.net.vn',
    'category': 'Workflow',
    'version': '18.1',
    'depends': ['hr', 'mail'],
    'category': 'Services',
    "images": [
        'static/description/icon.png'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/workflow_record_views.xml',
        'views/workflow_config_views.xml',
        'views/workflow_transition_views.xml',
        'views/workflow_history_views.xml',
        'templates/tier_validation_templates.xml',
        'views/menus.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'workflow_diagram/static/src/**/*'
        ]
    },
    'license': 'LGPL-3',
    'currency': 'EUR',
	'price': '200',
    'installable': True,
    'auto_install': False,
    'images': [
        'static/description/banner.jpg'
    ],
}
