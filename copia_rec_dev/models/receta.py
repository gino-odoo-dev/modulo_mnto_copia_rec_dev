from odoo import models, fields

class Receta(models.Model):
    _name = 'receta'
    _description = 'Receta'

    temporada_name = fields.Char(string='Nombre de Temporada', required=True)
