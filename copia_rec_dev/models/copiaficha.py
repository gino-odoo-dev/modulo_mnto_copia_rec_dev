from odoo import models, fields

class CopiaReceta(models.Model):
    _name = 'copia.receta' 
    _inherit = 'receta'  
    _description = 'Copia de Receta' 

    copia_nombre = fields.Char(string='Nombre de la copia', required=True)

    def copiar_receta(self):
        for record in self:
            nueva_receta = record-copy(default={'nombre_receta': f"Copia de {record.nombre_receta}"})
    