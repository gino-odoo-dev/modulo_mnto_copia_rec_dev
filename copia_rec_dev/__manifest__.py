{
    'name': 'Copia Ficha Tecnica',
    'version': '1.0',
    'summary': 'extension del modulo mantenimiento Copia ficha tecnica.',
    'description': 'Este modulo se extiende del modulo ficha tecnica para permitir la copia de recetas,',
    'author': 'MarcoAG',
    'depends': ['rec_dev'],
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
