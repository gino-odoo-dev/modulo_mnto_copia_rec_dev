from odoo import models, fields, api  
from odoo.exceptions import ValidationError  

class CopiaReceta(models.Model):
    _name = 'copia.receta' 
    _inherit = 'receta'  
    _description = 'Copia de Receta' 

# Campos del modelo
    part_o = fields.Char(string="Articulo Origen", required=True)
    part_d = fields.Char(string="Articulo Destino") 
    m_numero_color = fields.Boolean(string="Copiar Numeraciones/Ficha Tecnica") 
    temporada = fields.Char(string="Temporada", required=True)  
    copia = fields.Boolean(string="Copia") 
    m_modelo_o = fields.Char(string="Modelo Origen") 
    m_modelo_d = fields.Char(string="Modelo Destino") 
    no_comb_o = fields.Char(string="No Comb O")  
    no_comb_d = fields.Char(string="No Comb D") 
    remplaza = fields.Char(string="Remplaza")  
    mensaje = fields.Char(string="Mensaje", readonly=True) 
    xcuero = fields.Char(string="XCuero", size=3) 
    xcolor = fields.Char(string="XColor", size=3) 
    xplnta = fields.Char(string="XPlnta", size=3)  
    xcolfo = fields.Char(string="XColfo", size=3) 

# Metodo principal: copia_rec_dev
    def copia_rec_dev(self): 
        """
        Funcion de validaciones de campos, se valida temporada, articulo origen, articulo destino, estado de manufactura
        numero de origen y destino y numero de combinaciones.
        """
        self.ensure_one()  
        try:  
# Validar temporada
            if not self.temporada: 
                raise ValidationError("La temporada no puede estar vacia.") 
            
# Validar temporada exista en base de datos
            code_mstr_temporada = self.env['code_mstr'].search([
                ('code_domain', '=', 'global_domain'),
                ('code_fldname', '=', 'TEMPORADA'),
                ('code_value', '=', self.temporada)
            ], limit=1)
            if not code_mstr_temporada:
                raise ValidationError("La temporada no existe.")   
                    
# Validar articulo origen
            if not self.part_o:  
                raise ValidationError("El articulo origen no puede estar vacio.")
            if not self.part_o.startswith("PT-"):
                raise ValidationError("El articulo origen debe ser de tipo 'PT-'.")
            if self.pt_pm_code != 'M':
                raise ValidationError("El articulo origen debe estar marcado como manufacturado.")
            if not self.existe_estructura_para_temporada(self.part_o, self.temporada_especifica):
                raise ValidationError("La estructura no existe para la temporada.")
            
# Validar articulo destino (si no es copia de numero/color)
            if not self.m_numero_color and not self.part_d: 
                raise ValidationError("El artículo destino no puede estar vacio.")  

# Validar articulo destino (existencia, tipo, manufactura, numero y modelo)
            if not self.m_numero_color:
                articulo_destino = self.env['product.template'].search([('default_code', '=', self.part_d)], limit=1)
                if not articulo_destino:
                    raise ValidationError("El artículo destino no existe.")
                
# Tipo de articulo destino
                if not self.part_d.startswith("PT-"):
                    raise ValidationError("El articulo destino debe ser de tipo 'PT-'.")
                
# Estado de manufactura
                if articulo_destino.pt_pm_code != 'M':
                    raise ValidationError("El articulo destino debe estar marcado como manufacturado.")

# Numero de origen y destino deben ser iguales
                if self.part_o != self.part_d:
                    raise ValidationError("El numero de origen y destino deben ser iguales.")
                
# Modelo de origen y destino deben ser diferentes
                if self.m_modelo_o == self.m_modelo_d:
                    raise ValidationError("El modelo de origen y destino deben ser diferentes.")
                
# Numero de combinaciones debe coincidir
                no_comb_o = self.obtener_numero_combinaciones(self.part_o)  # Obtener combinaciones para el articulo origen
                no_comb_d = self.obtener_numero_combinaciones(self.part_d)  # Obtener combinaciones para el articulo destino
                if no_comb_o != no_comb_d:
                    raise ValidationError("El numero de combinaciones no coincide entre el articulo origen y el destino.")
                
# Logica de copia de numeros
            if self.m_numero_color:
                self._copia_numero(self.part_o, self.m_modelo_o) 
            else: 
# Logica de copia de colores
                self._copia_color(self.part_o, self.m_modelo_o, self.part_d, self.m_modelo_d)  # Llama al metodo _copia_color.
                self._cambia_materia(self.part_o, self.m_modelo_o, self.part_d, self.m_modelo_d)  # Llama al metodo _cambia_materia.
            self.mensaje = "Proceso de copia completado correctamente."  
        except ValidationError as e: 
            self.mensaje = f"Error de validacion: {str(e)}"  
        except Exception as e: 
            self.mensaje = f"Error inesperado: {str(e)}"


    def obtener_numero_combinaciones(self, codigo_articulo):
        """
        Metodo para obtener el numero de combinaciones de un articulo.
        :param codigo_articulo: Codigo del artículo (part_o o part_d).
        :return: Numero de combinaciones (str o None si no se encuentra).


        es necesaria para cumplir con la validacion del numero de combinaciones 
        entre el articulo origen y el articulo destino. 
        Esta validacion es crucial para garantizar que los articulos sean compatibles 
        antes de realizar la copia.
        """
# Buscar el articulo en la base de datos
        articulo = self.env['product.template'].search([('default_code', '=', codigo_articulo)], limit=1)
        
        if not articulo:
            raise ValidationError(f"El artículo {codigo_articulo} no existe.")
        
# Suponiendo que el numero de combinaciones esta en un campo personalizado llamado 'x_numero_combinaciones'
        if hasattr(articulo, 'x_numero_combinaciones'):
            return articulo.x_numero_combinaciones
        else:
            raise ValidationError(f"El artículo {codigo_articulo} no tiene un numero de combinaciones definido.")