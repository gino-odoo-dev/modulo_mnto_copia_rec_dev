{
    'name': 'Copia Ficha Tecnica',
    'version': '1.0',
    'summary': 'Modulo mantenimiento Copia ficha tecnica.',
    'description': 'Mantenimiento Copia Ficha Tecnica.',
    'author': 'MarcoAG',
    'depends': ['base', 'web', 'rec_dev'],
    'data': [
        'views/copia_rec_model_views.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'rec_dev/static/src/css/styles.css',
        ],
    },
    'installable': True,
    'application': True
}
