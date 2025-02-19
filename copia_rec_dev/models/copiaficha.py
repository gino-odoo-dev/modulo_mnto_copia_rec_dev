from odoo import models, fields

class Copiaficha(models.Model):
    _name = 'copia.ficha'
    _description = 'Copia ficha'

    name = fields.Char(string='Nombre', required=True)
