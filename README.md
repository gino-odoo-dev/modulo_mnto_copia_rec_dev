# Modulo Mantenimiento Copia Ficha Tecnica.

## Alcance del modulo

Modulo Copia Ficha Tecnica. 

## Modelos 

### `copiareceta.model`
- Fields:
  - `name` (Char)
  - `_decription` (Char)
  - `part_o` (Char)
  - `part_d` (Char)
  - `m_numero_color` (Boolean)
  - `temporada` (Char)
  - `copia` (Boolean)
  - `m_modelo_o` (Char)
  - `m_modelo_d` (Char)
  - `no_comb_o` (Char)
  - `no_comb_d` (Char)
  - `remplaza` (Char)
  - `mensaje` (Char)
  - `xcuero` (Char)
  - `xcolor` (Char)
  - `xplnta` (Char)
  - `xcolfo` (Char)
_________________________________________________

### `Funciones`

  - `_check_fields` ()
  - `copia_rec_dev` ()
  - `obtener_numero_combinaciones` ()
  - `_copia_numero` ()
  - `_cambia_componente` ()
  - `_crea_ficha_comp` ()
  - `_copia_color` ()
  - `_cambia_materia` ()
  - `_determinar_nuevo_componente` ()

_________________________________________________

### `Cuadro Comparacion "codigo progress-codigo python"`


![Cuadro Comparacion](./cuadro_comparacion.png)
