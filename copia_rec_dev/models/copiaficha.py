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

# Validar artículo origen
            if not self.part_o:
                raise ValidationError("El articulo origen no puede estar vacio.")
            if not self.part_o.startswith("PT-"):
                raise ValidationError("El articulo origen debe ser de tipo 'PT-'.")

# Obtener el artículo origen desde product.template
            articulo_origen = self.env['product.template'].search([('default_code', '=', self.part_o)], limit=1)
            if not articulo_origen:
                raise ValidationError("El articulo origen no existe.")

# Verificar el estado de manufactura del articulo origen
            if not hasattr(articulo_origen, 'pt_pm_code'):
                raise ValidationError("El campo 'pt_pm_code' no está definido en el articulo origen.")
            if articulo_origen.pt_pm_code != 'M':
                raise ValidationError("El articulo origen debe estar marcado como manufacturado.")

# Validar estructura para la temporada
            if not self.temporada(self.part_o, self.temporada):  # Usar self.temporada
                raise ValidationError("La estructura no existe para la temporada.")

# Validar articulo destino (si no es copia de número/color)
            if not self.m_numero_color and not self.part_d:
                raise ValidationError("El articulo destino no puede estar vacio.")

# Validar articulo destino (existencia, tipo, manufactura, numero y modelo)
            if not self.m_numero_color:
                articulo_destino = self.env['product.template'].search([('default_code', '=', self.part_d)], limit=1)
                if not articulo_destino:
                    raise ValidationError("El articulo destino no existe.")

# Tipo de articulo destino
                if not self.part_d.startswith("PT-"):
                    raise ValidationError("El articulo destino debe ser de tipo 'PT-'.")

# Estado de manufactura del artículo destino
                if not hasattr(articulo_destino, 'pt_pm_code'):
                    raise ValidationError("El campo 'pt_pm_code' no esta definido en el articulo destino.")
                if articulo_destino.pt_pm_code != 'M':
                    raise ValidationError("El articulo destino debe estar marcado como manufacturado.")

# Numero de origen y destino deben ser iguales
                if self.part_o != self.part_d:
                    raise ValidationError("El numero de origen y destino deben ser iguales.")

# Modelo de origen y destino deben ser diferentes
                if self.m_modelo_o == self.m_modelo_d:
                    raise ValidationError("El modelo de origen y destino deben ser diferentes.")

# Número de combinaciones debe coincidir
                no_comb_o = self.obtener_numero_combinaciones(self.part_o)
                no_comb_d = self.obtener_numero_combinaciones(self.part_d)
                if no_comb_o != no_comb_d:
                    raise ValidationError("El numero de combinaciones no coincide entre el articulo origen y el destino.")

# Crear ficha tecnica del componente destino si no existe
            self._crea_ficha_comp(self.part_o, self.part_d, self.temporada) 

# Logica de copia de números
            if self.m_numero_color:
                self._copia_numero(self.part_o, self.m_modelo_o)
            else:
# Logica de copia de colores
                self._copia_color(self.part_o, self.m_modelo_o, self.part_d, self.m_modelo_d)
                self._cambia_materia(self.part_o, self.m_modelo_o, self.part_d, self.m_modelo_d)
                self._cambia_componente(self.part_o, self.m_modelo_o, self.part_d, self.m_modelo_d)

            self.mensaje = "Proceso de copia completado correctamente."
        except ValidationError as e:
            self.mensaje = f"Error de validacion: {str(e)}"
        except Exception as e:
            self.mensaje = f"Error inesperado: {str(e)}"


    def obtener_numero_combinaciones(self, codigo_articulo):
        """
        Metodo para obtener el numero de combinaciones de un articulo.
        es necesaria para cumplir con la validacion del numero de combinaciones 
        entre el articulo origen y el articulo destino. 
        Esta validacion es crucial para garantizar que los articulos sean compatibles 
        antes de realizar la copia.
        """
# Buscar el articulo en la base de datos
        articulo = self.env['product.template'].search([('default_code', '=', codigo_articulo)], limit=1)
        
        if not articulo:
            raise ValidationError(f"El articulo {codigo_articulo} no existe.")
        
# Suponiendo que el numero de combinaciones esta en un campo personalizado llamado 'x_numero_combinaciones'
        if hasattr(articulo, 'x_numero_combinaciones'):
            return articulo.x_numero_combinaciones
        else:
            raise ValidationError(f"El artículo {codigo_articulo} no tiene un numero de combinaciones definido.")
        
# Metodo de copia 
    def _copia_numero(self, part_o, m_modelo_o):
        """
        Copia las formulas de un artículo origen a otros articulos del mismo modelo,
        excluyendo el artículo origen.
        """
# Validar que el artículo origen y el modelo sean validos
        if not part_o or not m_modelo_o:
            raise ValidationError("El articulo origen y el modelo son obligatorios.")

# Buscar registros en pt.mstr que cumplan con los filtros
        pt_mstr_records = self.env['pt.mstr'].search([
            ('pt_domain', '=', 'global_domain'),
            ('pt_model', '=', m_modelo_o),
            ('pt_part_type', '=like', 'PT-%'),
            ('pt_pm_code', '=', 'M'),
            ('pt_part', '!=', part_o)
        ])

# Borrar formulas antiguas de todos los demas numeros menos el origen
        for pt_record in pt_mstr_records:
            ps_mstr_records = self.env['ps.mstr'].search([
                ('ps_domain', '=', 'global_domain'),
                ('ps_par', '=', pt_record.pt_part),
                ('ps_ref', '=', self.temporada)
            ])
            ps_mstr_records.unlink()

# Crear nuevas formulas para los demas numeros
        ps_mstr_origin_records = self.env['ps.mstr'].search([
            ('ps_domain', '=', 'global_domain'),
            ('ps_par', '=', part_o),
            ('ps_ref', '=', self.temporada)
        ])

        for pt_record in pt_mstr_records:
            for ps_origin in ps_mstr_origin_records:
                self.env['ps.mstr'].create({
                    'ps_par': pt_record.pt_part,
                    'ps_comp': ps_origin.ps_comp,
                    'ps_ref': ps_origin.ps_ref,
                    'ps_qty_per': ps_origin.ps_qty_per,
                    'ps_scrp_pct': ps_origin.ps_scrp_pct,
                    'ps_ps_code': ps_origin.ps_ps_code,
                    'ps_lt_off': ps_origin.ps_lt_off,
                    'ps_start': ps_origin.ps_start,
                    'ps_end': ps_origin.ps_end,
                    'ps_rmks': ps_origin.ps_rmks,
                    'ps_op': ps_origin.ps_op,
                    'ps_item_no': ps_origin.ps_item_no,
                    'ps_mandatory': ps_origin.ps_mandatory,
                    'ps_exclusive': ps_origin.ps_exclusive,
                    'ps_process': ps_origin.ps_process,
                    'ps_qty_type': ps_origin.ps_qty_type,
                    'ps_user1': ps_origin.ps_user1,
                    'ps_user2': ps_origin.ps_user2,
                    'ps_fcst_pct': ps_origin.ps_fcst_pct,
                    'ps_default': ps_origin.ps_default,
                })

# Crear la tabla de cabecera (rec.mstr) si no existe
        for pt_record in pt_mstr_records:
            rec_mstr_record = self.env['rec.mstr'].search([
                ('rec_domain', '=', 'global_domain'),
                ('rec_parent', '=', pt_record.pt_part)
            ], limit=1)

            if not rec_mstr_record:
                rec_mstr_origin = self.env['rec.mstr'].search([
                    ('rec_domain', '=', 'global_domain'),
                    ('rec_parent', '=', part_o)
                ], limit=1)

                if rec_mstr_origin:
                    self.env['rec.mstr'].create({
                        'rec_parent': pt_record.pt_part,
                        'rec_desc': rec_mstr_origin.rec_desc,
                        'rec_batch': rec_mstr_origin.rec_batch,
                        'rec_batch_um': rec_mstr_origin.rec_batch_um,
                        'rec_cmtindx': rec_mstr_origin.rec_cmtindx,
                        'rec_ll_code': rec_mstr_origin.rec_ll_code,
                        'rec_user1': rec_mstr_origin.rec_user1,
                        'rec_user2': rec_mstr_origin.rec_user2,
                        'rec_userid': rec_mstr_origin.rec_userid,
                        'rec_mod_date': rec_mstr_origin.rec_mod_date,
                        'rec__chr01': rec_mstr_origin.rec__chr01,
                        'rec__chr02': rec_mstr_origin.rec__chr02,
                        'rec__chr03': rec_mstr_origin.rec__chr03,
                        'rec__chr04': rec_mstr_origin.rec__chr04,
                        'rec__chr05': rec_mstr_origin.rec__chr05,
                        'rec__dte01': rec_mstr_origin.rec__dte01,
                        'rec__dte02': rec_mstr_origin.rec__dte02,
                        'rec__dec01': rec_mstr_origin.rec__dec01,
                        'rec__dec02': rec_mstr_origin.rec__dec02,
                        'rec__log01': rec_mstr_origin.rec__log01,
                    })


    def _cambia_componente(self, part_o, m_modelo_o, part_d, m_modelo_d):
        """
        Cambia los componentes de una receta en la base de datos.   
        """
# Buscar las formulas del articulo origen
        ps_mstr_origin_records = self.env['ps.mstr'].search([
            ('ps_domain', '=', 'global_domain'),
            ('ps_par', '=', part_o),
            ('ps_ref', '=', self.temporada)
        ])

# Buscar las formulas del articulo destino
        ps_mstr_dest_records = self.env['ps.mstr'].search([
            ('ps_domain', '=', 'global_domain'),
            ('ps_par', '=', part_d),
            ('ps_ref', '=', self.temporada)
        ])

# Cambiar los componentes en las formulas del articulo destino
        for ps_dest in ps_mstr_dest_records:
            for ps_origin in ps_mstr_origin_records:
                if ps_dest.ps_comp == m_modelo_o:
                    ps_dest.write({
                        'ps_comp': m_modelo_d,
                        'ps_qty_per': ps_origin.ps_qty_per,
                        'ps_scrp_pct': ps_origin.ps_scrp_pct,
                        'ps_ps_code': ps_origin.ps_ps_code,
                        'ps_lt_off': ps_origin.ps_lt_off,
                        'ps_start': ps_origin.ps_start,
                        'ps_end': ps_origin.ps_end,
                        'ps_rmks': ps_origin.ps_rmks,
                        'ps_op': ps_origin.ps_op,
                        'ps_item_no': ps_origin.ps_item_no,
                        'ps_mandatory': ps_origin.ps_mandatory,
                        'ps_exclusive': ps_origin.ps_exclusive,
                        'ps_process': ps_origin.ps_process,
                        'ps_qty_type': ps_origin.ps_qty_type,
                        'ps_user1': ps_origin.ps_user1,
                        'ps_user2': ps_origin.ps_user2,
                        'ps_fcst_pct': ps_origin.ps_fcst_pct,
                        'ps_default': ps_origin.ps_default,
                    })

    def _crea_ficha_comp(self, comp_origen, comp_destino, temporada):
        """
        Crea la ficha tecnica del componente destino basada en el componente origen.
        """
# Buscar la ficha tecnica del componente destino
        ps_mstr_destino = self.env['ps.mstr'].search([
            ('ps_domain', '=', 'global_domain'),
            ('ps_par', '=', comp_destino),
            ('ps_ref', '=', temporada)
        ], limit=1)

# Si no existe la ficha tecnica del componente destino, se procede a crearla
        if not ps_mstr_destino:
            ps_mstr_origen_records = self.env['ps.mstr'].search([
                ('ps_domain', '=', 'global_domain'),
                ('ps_par', '=', comp_origen),
                ('ps_ref', '=', temporada)
            ])

            for ps_origen in ps_mstr_origen_records:
# Determinar si se debe cambiar el numero del componente
                comp_cambia_num = (
                    ps_origen.ps_comp[-3:] == comp_origen[-3:]
                )
                comp_numero = comp_destino[-3:] if comp_cambia_num else ""

# Crear la nueva ficha tecnica para el componente destino
                self.env['ps.mstr'].create({
                    'ps_par': comp_destino,
                    'ps_comp': (
                        ps_origen.ps_comp[:-3] + comp_numero
                        if comp_cambia_num else ps_origen.ps_comp
                    ),
                    'ps_ref': ps_origen.ps_ref,
                    'ps_qty_per': ps_origen.ps_qty_per,
                    'ps_scrp_pct': ps_origen.ps_scrp_pct,
                    'ps_ps_code': ps_origen.ps_ps_code,
                    'ps_lt_off': ps_origen.ps_lt_off,
                    'ps_start': ps_origen.ps_start,
                    'ps_end': ps_origen.ps_end,
                    'ps_rmks': ps_origen.ps_rmks,
                    'ps_op': ps_origen.ps_op,
                    'ps_item_no': ps_origen.ps_item_no,
                    'ps_mandatory': ps_origen.ps_mandatory,
                    'ps_exclusive': ps_origen.ps_exclusive,
                    'ps_process': ps_origen.ps_process,
                    'ps_qty_type': ps_origen.ps_qty_type,
                    'ps_user1': ps_origen.ps_user1,
                    'ps_user2': ps_origen.ps_user2,
                    'ps_fcst_pct': ps_origen.ps_fcst_pct,
                    'ps_default': ps_origen.ps_default,
                    'ps_group': ps_origen.ps_group,
                    'ps_critical': ps_origen.ps_critical,
                    'ps_qty_per_b': ps_origen.ps_qty_per_b,
                    'ps_comp_um': ps_origen.ps_comp_um,
                    'ps_um_conv': ps_origen.ps_um_conv,
                    'ps_assay': ps_origen.ps_assay,
                    'ps_comm_code': ps_origen.ps_comm_code,
                    'ps_non_bal': ps_origen.ps_non_bal,
                    'ps__qad01': ps_origen.ps__qad01,
                    'ps_userid': ps_origen.ps_userid,
                    'ps_mod_date': ps_origen.ps_mod_date,
                    'ps_batch_pct': ps_origen.ps_batch_pct,
                    'ps_cmtindx': ps_origen.ps_cmtindx,
                    'ps_start_ecn': ps_origen.ps_start_ecn,
                    'ps_end_ecn': ps_origen.ps_end_ecn,
                    'ps_joint_type': ps_origen.ps_joint_type,
                    'ps_cop_qty': ps_origen.ps_cop_qty,
                    'ps_cst_pct': ps_origen.ps_cst_pct,
                    'ps_prod_pct': ps_origen.ps_prod_pct,
                    'ps_qty_cons': ps_origen.ps_qty_cons,
                    'ps_qty_exch': ps_origen.ps_qty_exch,
                    'ps_qty_diag': ps_origen.ps_qty_diag,
                    'ps__chr01': ps_origen.ps__chr01,
                    'ps__chr02': ps_origen.ps__chr02,
                    'ps__dte01': ps_origen.ps__dte01,
                    'ps__dte02': ps_origen.ps__dte02,
                    'ps__dec01': ps_origen.ps__dec01,
                    'ps__dec02': ps_origen.ps__dec02,
                    'ps__log01': ps_origen.ps__log01,
                    'ps__log02': ps_origen.ps__log02,
                    'ps__qadc01': ps_origen.ps__qadc01,
                    'ps__qadc02': ps_origen.ps__qadc02,
                    'ps__qadt01': ps_origen.ps__qadt01,
                    'ps__qadt02': ps_origen.ps__qadt02,
                    'ps__qadt03': ps_origen.ps__qadt03,
                    'ps__qadd01': ps_origen.ps__qadd01,
                    'ps__qadd02': ps_origen.ps__qadd02,
                    'ps__qadl01': ps_origen.ps__qadl01,
                    'ps__qadl02': ps_origen.ps__qadl02,
                    'ps_domain': ps_origen.ps_domain,
                    'oid_ps_mstr': ps_origen.oid_ps_mstr,
                })

# Crear la tabla de cabecera (bom_mstr) si no existe
                bom_mstr_destino = self.env['bom.mstr'].search([
                    ('bom_domain', '=', 'global_domain'),
                    ('bom_parent', '=', comp_destino)
                ], limit=1)

                if not bom_mstr_destino:
                    bom_mstr_origen = self.env['bom.mstr'].search([
                        ('bom_domain', '=', 'global_domain'),
                        ('bom_parent', '=', comp_origen)
                    ], limit=1)

                    if bom_mstr_origen:
                        self.env['bom.mstr'].create({
                            'bom_parent': comp_destino,
                            'bom_desc': bom_mstr_origen.bom_desc,
                            'bom_batch': bom_mstr_origen.bom_batch,
                            'bom_batch_um': bom_mstr_origen.bom_batch_um,
                            'bom_cmtindx': bom_mstr_origen.bom_cmtindx,
                            'bom_ll_code': bom_mstr_origen.bom_ll_code,
                            'bom_user1': bom_mstr_origen.bom_user1,
                            'bom_user2': bom_mstr_origen.bom_user2,
                            'bom_userid': bom_mstr_origen.bom_userid,
                            'bom_mod_date': bom_mstr_origen.bom_mod_date,
                            'bom__chr01': bom_mstr_origen.bom__chr01,
                            'bom__chr02': bom_mstr_origen.bom__chr02,
                            'bom__chr03': bom_mstr_origen.bom__chr03,
                            'bom__chr04': bom_mstr_origen.bom__chr04,
                            'bom__chr05': bom_mstr_origen.bom__chr05,
                            'bom__dte01': bom_mstr_origen.bom__dte01,
                            'bom__dte02': bom_mstr_origen.bom__dte02,
                            'bom__dec01': bom_mstr_origen.bom__dec01,
                            'bom__dec02': bom_mstr_origen.bom__dec02,
                            'bom__log01': bom_mstr_origen.bom__log01,
                            'bom_formula': bom_mstr_origen.bom_formula,
                            'bom_mthd': bom_mstr_origen.bom_mthd,
                            'bom_fsm_type': bom_mstr_origen.bom_fsm_type,
                            'bom_site': bom_mstr_origen.bom_site,
                            'bom_loc': bom_mstr_origen.bom_loc,
                            'bom__qadc01': bom_mstr_origen.bom__qadc01,
                            'bom__qadc02': bom_mstr_origen.bom__qadc02,
                            'bom__qadc03': bom_mstr_origen.bom__qadc03,
                            'bom__qadd01': bom_mstr_origen.bom__qadd01,
                            'bom__qadi01': bom_mstr_origen.bom__qadi01,
                            'bom__qadi02': bom_mstr_origen.bom__qadi02,
                            'bom__qadt01': bom_mstr_origen.bom__qadt01,
                            'bom__qadt02': bom_mstr_origen.bom__qadt02,
                            'bom__qadl01': bom_mstr_origen.bom__qadl01,
                            'bom__qadl02': bom_mstr_origen.bom__qadl02,
                            'bom_mthd_qtycompl': bom_mstr_origen.bom_mthd_qtycompl,
                            'bom_domain': bom_mstr_origen.bom_domain,
                            'oid_bom_mstr': bom_mstr_origen.oid_bom_mstr,
                        })
                        

    def _copia_color(self, part_o, m_modelo_o, part_d, m_modelo_d): 
# Borrar formulas antiguas del articulo destino
        ps_mstr_records = self.env['ps.mstr'].search([  
            ('ps_domain', '=', 'global_domain'), 
            ('ps_par', '=', part_d), 
            ('ps_ref', '=', self.temporada) 
        ])
        ps_mstr_records.unlink() 
# Copiar formulas del articulo origen al destino
        ps_mstr_origin_records = self.env['ps.mstr'].search([ 
            ('ps_domain', '=', 'global_domain'), 
            ('ps_par', '=', part_o), 
            ('ps_ref', '=', self.temporada) 
        ])

        for ps_origin in ps_mstr_origin_records: 
            self.env['ps.mstr'].create({ 
                'ps_par': part_d,  
                'ps_comp': m_modelo_d if ps_origin.ps_comp == m_modelo_o else ps_origin.ps_comp, 
                'ps_ref': ps_origin.ps_ref, 
                'ps_qty_per': ps_origin.ps_qty_per, 
                'ps_scrp_pct': ps_origin.ps_scrp_pct,  
                'ps_ps_code': ps_origin.ps_ps_code, 
                'ps_lt_off': ps_origin.ps_lt_off,  
                'ps_start': ps_origin.ps_start, 
                'ps_end': ps_origin.ps_end, 
                'ps_rmks': ps_origin.ps_rmks,  
                'ps_op': ps_origin.ps_op, 
                'ps_item_no': ps_origin.ps_item_no, 
                'ps_mandatory': ps_origin.ps_mandatory,  
                'ps_exclusive': ps_origin.ps_exclusive, 
                'ps_process': ps_origin.ps_process, 
                'ps_qty_type': ps_origin.ps_qty_type, 
                'ps_user1': ps_origin.ps_user1,
                'ps_user2': ps_origin.ps_user2, 
                'ps_fcst_pct': ps_origin.ps_fcst_pct, 
                'ps_default': ps_origin.ps_default, 
            })

    def _cambia_materia(self, part_o, m_modelo_o, part_d, m_modelo_d):
        """
        Cambia las materias primas de un articulo según las reglas definidas.         
        """
# Buscar las fórmulas del artículo destino
        ps_mstr_records = self.env['ps.mstr'].search([
            ('ps_domain', '=', 'global_domain'),
            ('ps_par', '=', part_d),
            ('ps_ref', '=', self.temporada)
        ])

        for ps_record in ps_mstr_records:
# Buscar el componente actual en pt.mstr
            pt_record = self.env['pt.mstr'].search([
                ('pt_domain', '=', 'global_domain'),
                ('pt_part', '=', ps_record.ps_comp),
# Filtra por grupo (Tacos, Contrafuerte, Puntaduras)
                ('pt_group', 'in', ['115', '020', '109'])
            ], limit=1)

            if pt_record:
# Lógica para determinar el nuevo componente
                nuevo_componente = self._determinar_nuevo_componente(pt_record)
                
                if nuevo_componente:
# Actualizar el componente en la formula
                    ps_record.write({'ps_comp': nuevo_componente})
                else:
                    raise ValidationError(f"No se pudo determinar un nuevo componente para {pt_record.pt_part}.")

    def _determinar_nuevo_componente(self, pt_record):
        """
        Determina el nuevo componente basado en el componente actual.
        """
# Caso 1: Buscar un componente alternativo en el mismo grupo
        nuevo_componente = self.env['pt.mstr'].search([
            ('pt_domain', '=', 'global_domain'),
            ('pt_group', '=', pt_record.pt_group),  
            ('pt_part', '!=', pt_record.pt_part),  
        ], limit=1)

        if nuevo_componente:
            return nuevo_componente.pt_part

#  Usar un mapeo predefinido
        mapeo_componentes = {
            'COMPONENTE_ANTIGUO_1': 'COMPONENTE_NUEVO_1',
            'COMPONENTE_ANTIGUO_2': 'COMPONENTE_NUEVO_2',
        }

        if pt_record.pt_part in mapeo_componentes:
            return mapeo_componentes[pt_record.pt_part]

#  Generar el nuevo componente
#  Agregar un sufijo o prefijo al codigo original
        if pt_record.pt_part.startswith("PT-"):
            return f"PT-NUEVO-{pt_record.pt_part[3:]}"
# Si no se encuentra un nuevo componente, devolver None
        return None
    
