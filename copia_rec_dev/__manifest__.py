{
    'name': 'Copia Ficha Tecnica',
    'version': '1.0',
    'summary': 'extension del modulo mantenimiento Copia ficha tecnica (receta_dev).',
    'description': 'Este modulo se extiende del modulo ficha tecnica para permitir la copia de recetas,',
    'author': 'MarcoAG',
    'depends': [
        'receta_dev'
    ],
    'data': [
        'views/copia_rec_model_views.xml',
        'security/ir.model.access.csv',
    ],
    
    'installable': True,
    'application': True
}
