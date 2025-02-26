from odoo import models, fields, api
from odoo.exceptions import ValidationError

class CopiaReceta(models.Model):
    _name = 'copia.receta'
    _description = 'Copia de Receta'

    part_o = fields.Char(string="Articulo Origen", required=True)
    part_d = fields.Char(string="Articulo Destino")
    m_numero_color = fields.Boolean(string="Copiar Numeraciones/Ficha Tecnica", default=True)
    temporada = fields.Char(string="Temporada", required=True)
    copia = fields.Boolean(string="Copia")
    m_modelo_o = fields.Char(string="Modelo Origen")
    m_modelo_d = fields.Char(string="Modelo Destino")
    no_comb_o = fields.Char(string="Numero Combinaciones Origen")
    no_comb_d = fields.Char(string="Numero Combinaciones Destino")
    remplaza = fields.Char(string="Remplaza")
    mensaje = fields.Char(string="Mensaje", readonly=True)
    xcuero = fields.Char(string="XCuero", size=3)
    xcolor = fields.Char(string="XColor", size=3)
    xplnta = fields.Char(string="XPlnta", size=3)
    xcolfo = fields.Char(string="XColfo", size=3)

    
    def copia_rec_dev(self):
        """
        Funcion principal que realiza las validaciones y copia de recetas.
        """
        self.ensure_one()
        try:
# Validar que la temporada exista en la base de datos
            temporada_existente = self.env['code.mstr'].search([
                ('code_domain', '=', 'global_domain'),
                ('code_fldname', '=', 'TEMPORADA'),
                ('code_value', '=', self.temporada)
            ], limit=1)
            if not temporada_existente:
                raise ValidationError("La temporada no existe.")

# Validar articulo origen
            if not self.part_o:
                raise ValidationError("El artículo origen no puede estar vacío.")
            articulo_origen = self.env['product.template'].search([('default_code', '=', self.part_o)], limit=1)
            if not articulo_origen:
                raise ValidationError("El artículo origen no existe.")
            if not articulo_origen.pt_part_type.startswith("PT-"):
                raise ValidationError("El artículo origen debe ser de tipo 'PT-'.")
            if articulo_origen.pt_pm_code != 'M':
                raise ValidationError("El artículo origen debe estar marcado como manufacturado.")

# Validar estructura para la temporada
            estructura_existente = self.env['ps.mstr'].search([
                ('ps_domain', '=', 'global_domain'),
                ('ps_par', '=', self.part_o),
                ('ps_ref', '=', self.temporada)
            ], limit=1)
            if not estructura_existente:
                raise ValidationError("El artículo origen no tiene estructura para la temporada.")

# Validar articulo destino (si no es copia de número/color)
            if not self.m_numero_color:
                if not self.part_d:
                    raise ValidationError("El artículo destino no puede estar vacío.")
                articulo_destino = self.env['product.template'].search([('default_code', '=', self.part_d)], limit=1)
                if not articulo_destino:
                    raise ValidationError("El artículo destino no existe.")
                if not articulo_destino.pt_part_type.startswith("PT-"):
                    raise ValidationError("El artículo destino debe ser de tipo 'PT-'.")
                if articulo_destino.pt_pm_code != 'M':
                    raise ValidationError("El artículo destino debe estar marcado como manufacturado.")
                if self.part_o == self.part_d:
                    raise ValidationError("El artículo origen y destino no pueden ser iguales.")
                if self.m_modelo_o == self.m_modelo_d:
                    raise ValidationError("El modelo de origen y destino deben ser diferentes.")

# Validar numero de combinaciones
                if self.no_comb_o != self.no_comb_d:
                    raise ValidationError("El número de combinaciones no coincide entre el artículo origen y destino.")

# Logica de copia
            if self.m_numero_color:
                self._copia_numero(self.part_o, self.m_modelo_o)
            else:
                self._copia_color(self.part_o, self.m_modelo_o, self.part_d, self.m_modelo_d)
                self._cambia_materia(self.part_o, self.m_modelo_o, self.part_d, self.m_modelo_d)
                self._cambia_componente(self.part_o, self.m_modelo_o, self.part_d, self.m_modelo_d)

            self.mensaje = "Proceso de copia completado correctamente."
        except ValidationError as e:
            self.mensaje = f"Error de validación: {str(e)}"
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
           
    def _copia_numero(self, part_o, temporada):
        """
        Copia las fórmulas de un artículo origen a otros artículos del mismo modelo.
        """
        articulos_mismo_modelo = self.env['product.template'].search([
            ('pt_model', '=', self.env['product.template'].browse([('default_code', '=', part_o)]).pt_model),
            ('pt_part_type', '=like', 'PT-%'),
            ('pt_pm_code', '=', 'M'),
            ('default_code', '!=', part_o)
        ])

# Copiar formulas
        for articulo in articulos_mismo_modelo:
            formulas_origen = self.env['ps.mstr'].search([
                ('ps_domain', '=', 'global_domain'),
                ('ps_par', '=', part_o),
                ('ps_ref', '=', temporada)
            ])
            for formula in formulas_origen:
                self.env['ps.mstr'].create({
                    'ps_par': articulo.default_code,
                    'ps_comp': formula.ps_comp,
                    'ps_ref': formula.ps_ref,
                    'ps_qty_per': formula.ps_qty_per,
                    'ps_scrp_pct': formula.ps_scrp_pct,
                    'ps_ps_code': formula.ps_ps_code,
                    'ps_lt_off': formula.ps_lt_off,
                    'ps_start': formula.ps_start,
                    'ps_end': formula.ps_end,
                    'ps_rmks': formula.ps_rmks,
                    'ps_op': formula.ps_op,
                    'ps_item_no': formula.ps_item_no,
                    'ps_mandatory': formula.ps_mandatory,
                    'ps_exclusive': formula.ps_exclusive,
                    'ps_process': formula.ps_process,
                    'ps_qty_type': formula.ps_qty_type,
                    'ps_user1': formula.ps_user1,
                    'ps_user2': formula.ps_user2,
                    'ps_fcst_pct': formula.ps_fcst_pct,
                    'ps_default': formula.ps_default,
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
# Buscar un componente alternativo
                    nuevo_componente = self._determinar_nuevo_componente(ps_origin.ps_comp)
                    if nuevo_componente:
                        ps_dest.write({
                            'ps_comp': nuevo_componente,
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
                    else:
                        raise ValidationError(f"No se pudo determinar un nuevo componente para {ps_origin.ps_comp}.")

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

# Si ya existe la ficha tecnica del componente destino, lanzar una excepcion
        if ps_mstr_destino:
            raise ValidationError(f"La ficha técnica del componente destino {comp_destino} ya existe para la temporada {temporada}.")

# Si no existe la ficha tecnica del componente destino, se procede a crearla
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
                        
    def _copia_color(self, part_o, part_d, temporada):
        """
        Copia las formulas de un articulo origen a un articulo destino.
        """
# Copiar formulas del articulo origen al destino
        formulas_origen = self.env['ps.mstr'].search([
            ('ps_domain', '=', 'global_domain'),
            ('ps_par', '=', part_o),
            ('ps_ref', '=', temporada)
        ])
        for formula in formulas_origen:
            self.env['ps.mstr'].create({
                'ps_par': part_d,
                'ps_comp': formula.ps_comp,
                'ps_ref': formula.ps_ref,
                'ps_qty_per': formula.ps_qty_per,
                'ps_scrp_pct': formula.ps_scrp_pct,
                'ps_ps_code': formula.ps_ps_code,
                'ps_lt_off': formula.ps_lt_off,
                'ps_start': formula.ps_start,
                'ps_end': formula.ps_end,
                'ps_rmks': formula.ps_rmks,
                'ps_op': formula.ps_op,
                'ps_item_no': formula.ps_item_no,
                'ps_mandatory': formula.ps_mandatory,
                'ps_exclusive': formula.ps_exclusive,
                'ps_process': formula.ps_process,
                'ps_qty_type': formula.ps_qty_type,
                'ps_user1': formula.ps_user1,
                'ps_user2': formula.ps_user2,
                'ps_fcst_pct': formula.ps_fcst_pct,
                'ps_default': formula.ps_default,
            })

# Borrar formulas antiguas del articulo destino solo si la copia fue exitosa
        self.env['ps.mstr'].search([
            ('ps_domain', '=', 'global_domain'),
            ('ps_par', '=', part_d),
            ('ps_ref', '=', temporada),
            ('id', 'not in', [f.id for f in formulas_origen])
        ]).unlink()

    def _cambia_materia(self, part_o, m_modelo_o, part_d, m_modelo_d):
        """
        Cambia las materias primas de un articulo segun las reglas definidas.
        """
# Buscar las formulas del articulo destino
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
# Logica para determinar el nuevo componente
                nuevo_componente = self._determinar_nuevo_componente(pt_record)
                
                if nuevo_componente:
# Actualizar el componente en la formula
                    ps_record.write({'ps_comp': nuevo_componente})
                else:
                    raise ValidationError(f"No se pudo determinar un nuevo componente para {pt_record.pt_part}.")
            else:
                raise ValidationError(f"No se encontró el componente actual {ps_record.ps_comp} en pt.mstr.")

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

# Caso 2: Usar un mapeo predefinido
        mapeo_componentes = {
            'COMPONENTE_ANTIGUO_1': 'COMPONENTE_NUEVO_1',
            'COMPONENTE_ANTIGUO_2': 'COMPONENTE_NUEVO_2',
        }

        if pt_record.pt_part in mapeo_componentes:
            return mapeo_componentes[pt_record.pt_part]

# Caso 3: Generar el nuevo componente
# Agregar un sufijo o prefijo al código original
        if pt_record.pt_part.startswith("PT-"):
            return f"PT-NUEVO-{pt_record.pt_part[3:]}"

# Si no se encuentra un nuevo componente, devolver None
        return None
    