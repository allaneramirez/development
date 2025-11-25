# Localización Fiscal Hondureña

Módulo completo para Odoo 16 y Odoo 17 que automatiza todos los requisitos fiscales del **Servicio de Administración de Rentas (SAR)** de Honduras, incluyendo facturación DPS, gestión de CAI, libros fiscales y reportes PT.

## 📋 Tabla de Contenidos

1. [Características Principales](#características-principales)
2. [Instalación](#instalación)
3. [Configuración Inicial](#configuración-inicial)
4. [Gestión de CAI](#gestión-de-cai)
5. [Factura DPS](#factura-dps)
6. [Libros Fiscales](#libros-fiscales)
7. [Campos Adicionales](#campos-adicionales)
8. [Estructura del Módulo](#estructura-del-módulo)
9. [Flujo de Trabajo](#flujo-de-trabajo)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Características Principales

### 1. Factura DPS (Documento Pre-impreso)

Reporte de factura con diseño pre-impreso personalizado que cumple con los requisitos del SAR:

- **Imagen de fondo embebida**: Carga automática de `factura_dps_backgroup.png` como base64 para renderizado confiable en PDF
- **Fuentes personalizadas**: Integración de Poppins Regular y Bold desde archivos estáticos
- **Posicionamiento absoluto**: Todos los elementos posicionados en centímetros para alineación precisa con papel pre-impreso
- **Secciones organizadas**:
  - Datos de la compañía (superior derecha)
  - Nombre del documento fiscal y número
  - Información del cliente (nombre, dirección, RTN)
  - Sección de Datos del Adquiriente Exonerado
  - Tabla de líneas de productos con encabezado teal oscuro (#004257)
  - Footer con observaciones, total en letras, datos CAI y totales
- **Selección centralizada del reporte**: Se añade el campo *Reporte de Factura de Venta* en `Ajustes → Contabilidad → Facturas de cliente`, lo que permite definir que la *Factura DPS* sea el informe predeterminado para todas las facturas de cliente.
- **Visibilidad controlada**: El informe DPS está restringido al grupo `base.group_system`, garantizando que solo usuarios administradores puedan imprimirlo o modificarlo.

**Métodos Python implementados**:
- `get_dps_background_image()`: Carga la imagen de fondo como base64
- `get_poppins_regular_font()` / `get_poppins_bold_font()`: Carga fuentes como base64
- `get_document_name_dps()`: Determina dinámicamente el nombre del documento (FACTURA, NOTA DE CRÉDITO, NOTA DE DÉBITO)
- `get_formatted_date_dps()`: Formatea la fecha en español (ej: "15 de enero de 2024")

### 2. Gestión de CAI (Código de Autorización de Impresión)

Sistema completo de gestión de CAI con validaciones y controles:

- **Estados del CAI**: Borrador y Confirmado
- **Validación de rangos**: Control automático del rango autorizado (correlativo inicial y final)
- **Validación de fechas**: Verificación de fecha límite de emisión
- **Asociación con secuencias**: Los CAI se vinculan a secuencias de diarios
- **Bloqueo de secuencias**: Las secuencias con CAI confirmado no pueden modificarse
- **Establecimientos y Puntos de Emisión**: Gestión jerárquica de ubicaciones fiscales
- **Cálculo automático**: Próximo número a emitir, números restantes, último número usado

**Modelo**: `l10n_hn.cai`

**Campos principales**:
- `name`: Código CAI (37 caracteres)
- `state`: Estado (draft/confirmed)
- `journal_id`: Diario asociado
- `sequence_id`: Secuencia vinculada
- `fiscal_document_type_id`: Tipo de documento fiscal
- `emition`: Fecha de recepción
- `emition_limit`: Fecha límite de emisión
- `range_start` / `range_end`: Rango autorizado
- `establecimiento_id`: Código de establecimiento
- `punto_emision_id`: Punto de emisión

### 3. Tipos de Documentos Fiscales

Configuración de tipos de documentos según normativa del SAR:

- **Modelo**: `fiscal_document_type`
- **Campos**: Nombre, código, tipo interno (invoice/debit_note/credit_note)
- **Validaciones**: Código y nombre únicos por país
- **Asociación**: Se vinculan a CAI y secuencias

### 4. Establecimientos y Puntos de Emisión

Gestión jerárquica de ubicaciones fiscales:

- **Establecimientos** (`l10n_hn.establecimiento`):
  - Código de establecimiento (3 dígitos)
  - Nombre comercial
  - Dirección fiscal
  - Relación con puntos de emisión

- **Puntos de Emisión** (`l10n_hn.punto.emision`):
  - Código de punto de emisión (3 dígitos)
  - Nombre del punto
  - Vinculado a un establecimiento

### 5. Libros Fiscales

#### 5.1. Libro de Ventas

**Formatos disponibles**:
- **PDF**: Libro tradicional con formato oficial
- **Excel (XLSX)**: Versión editable del registro
- **PT Excel**: Libro PT con validaciones y columnas adicionales

**Columnas del PT Libro Ventas**:
- Fecha
- Número de documento (con desglose automático: Establecimiento, Punto de Emisión, Tipo, Correlativo)
- RTN del cliente (formateado: XXXXX-XXXXXX-X)
- Nombre del cliente
- Importe Exonerado
- Importe Exento
- Importe Gravado 15%
- Importe Gravado 18%
- ISV 15%
- ISV 18%
- Total
- **Producto**: Código cuenta y Nombre de cuenta (de `account_id` de cada línea)
- **Condición de Pago**: Términos de pago de la factura

#### 5.2. Libro de Compras

**Formatos disponibles**:
- **PDF**: Libro tradicional con formato oficial
- **Excel (XLSX)**: Versión editable del registro
- **PT Excel**: Libro PT con conciliación contable

**Características del PT Libro Compras**:
- Conciliación del ISV declarado vs. asiento contable
- Detalle de debe/haber
- Columnas de observaciones editables
- Validación cruzada de datos
- Columnas dinámicas derivadas del número de documento (`ref`)

### 6. Configuración de Libros

Sistema flexible de configuración que permite:
- Filtrar por diarios específicos
- Filtrar por impuestos (ISV 15%, ISV 18%, Exento, Exonerado)
- Configuraciones separadas para ventas y compras
- Validación automática de tipos (solo diarios/impuestos del tipo correspondiente)

---

## 🚀 Instalación

### Requisitos Previos

- Odoo 16.0 o superior (compatible con Odoo 17)
- Módulos base requeridos:
  - `base`
  - `account`
  - `portal`
  - `account_move_name_sequence`
  - `res_partner_type_store`
  - `l10n_latam_base`

### Pasos de Instalación

1. **Copiar el módulo**:
   ```bash
   cp -r l10n_hn_fiscal /ruta/a/tus/addons/
   ```

2. **Actualizar lista de aplicaciones**:
   - En Odoo: `Aplicaciones → Actualizar lista de aplicaciones`

3. **Instalar el módulo**:
   - Buscar "Localización Fiscal Hondureña"
   - Clic en "Instalar"

4. **Asignar permisos**:
   - Ir a `Configuración → Usuarios y Compañías → Usuarios`
   - Editar usuarios que gestionarán información fiscal
   - Asignar grupo: `l10n_hn_fiscal.group_show_l10n_hn_fiscal`

---

## ⚙️ Configuración Inicial

### 1. Datos Fiscales de la Compañía

**Ruta**: `Ajustes → Contabilidad → Facturas de cliente`

En el grupo (nuevo) que se muestra al inicio de esta sección:

- **RTN**: Registro Tributario Nacional
- **Colores corporativos**: Para personalización de reportes (opcional)
- **Reporte de Factura de Venta**: Selecciona "Factura DPS" para que sea el reporte que se imprima por defecto desde los menús de facturación.

> ℹ️ Solo los usuarios del grupo Administradores/Settings (`base.group_system`) verán y podrán modificar esta configuración.

### 2. Establecimientos y Puntos de Emisión

**Ruta**: `Contabilidad → Configuración → Establecimientos Fiscales HN`

1. **Crear Establecimiento**:
   - Código de Establecimiento (3 dígitos)
   - Nombre Comercial
   - Dirección Fiscal (debe ser un contacto hijo de la compañía)

2. **Crear Puntos de Emisión**:
   - Seleccionar el Establecimiento
   - Código de Punto de Emisión (3 dígitos)
   - Nombre del Punto

### 3. Tipos de Documentos Fiscales

**Ruta**: `Contabilidad → Configuración → Documentos Fiscales HN`

Define los tipos de documentos admitidos por el SAR:

| Tipo | Código | Tipo Interno | Descripción |
|------|--------|--------------|-------------|
| Factura | FAC | invoice | Factura de venta normal |
| Nota de Crédito | NCR | credit_note | Nota de crédito |
| Nota de Débito | NDB | debit_note | Nota de débito |
| Factura de Exportación | FEX | invoice | Factura de exportación |

**Configuración**:
- Nombre: Nombre completo del documento
- Código: Código de 3 caracteres
- Tipo Interno: invoice, credit_note o debit_note
- País: Honduras (HN)

### 4. Configuración de Diarios

**Ruta**: `Contabilidad → Configuración → Diarios`

Para cada diario de ventas:

1. **Configurar Secuencia**:
   - Ir a la pestaña "Secuencia"
   - Marcar "Documento Fiscal" (`active_sar`)
   - Seleccionar "Tipo de Documento Fiscal"
   - Configurar prefijo y formato

2. **Asignar CAI** (ver sección siguiente)

### 5. Configuración de Libros

**Ruta**: `Contabilidad → Configuración → Configuración de Registro de Compras y Ventas`

#### Para Libro de Ventas:

1. Crear nueva configuración
2. Tipo de Reporte: `Invoice Sales Report`
3. Seleccionar Diarios: Solo diarios de tipo "Ventas"
4. Seleccionar Impuestos: ISV 15%, ISV 18%, EXE (Exento), EXO (Exonerado)
5. Guardar

#### Para Libro de Compras:

1. Crear nueva configuración
2. Tipo de Reporte: `Invoice Purchase Report`
3. Seleccionar Diarios: Solo diarios de tipo "Compras"
4. Seleccionar Impuestos: ISV 15%, ISV 18%, EXE (Exento), EXO (Exonerado)
5. Guardar

---

## 🎫 Gestión de CAI

### Crear un CAI

**Ruta**: `Contabilidad → Configuración → CAI`

1. **Crear nuevo CAI**:
   - CAI: Ingresar el código de 37 caracteres
   - Diario: Seleccionar el diario de ventas
   - Tipo de Documento Fiscal: Seleccionar el tipo correspondiente
   - Establecimiento: Seleccionar el establecimiento
   - Punto de Emisión: Seleccionar el punto (filtrado por establecimiento)
   - Fecha de Recepción: Fecha en que se recibió el CAI
   - Fecha Límite de Emisión: Fecha hasta la cual se puede usar
   - Número Inicial: Primer número del rango autorizado
   - Número Final: Último número del rango autorizado
   - Declaración: (Opcional) Campo de 8 caracteres

2. **Asociar Secuencia**:
   - Seleccionar la secuencia del diario
   - El sistema validará que la secuencia tenga el mismo tipo de documento

3. **Confirmar CAI**:
   - Clic en "Confirmar"
   - El sistema:
     - Genera un hash de confirmación
     - Actualiza la secuencia con los datos del CAI
     - Bloquea la secuencia para edición
     - Calcula el próximo número a emitir

### Estados del CAI

- **Borrador**: CAI creado pero no confirmado. Puede editarse libremente.
- **Confirmado**: CAI activo y vinculado a una secuencia. La secuencia queda bloqueada.

### Restablecer CAI a Borrador

**Ruta**: `Contabilidad → Configuración → CAI → [Seleccionar CAI] → Restablecer a Borrador`

- Requiere el hash de confirmación
- Libera la secuencia para edición
- Permite modificar los datos del CAI

### Validaciones Automáticas

El sistema valida automáticamente:

1. **Al generar número de secuencia**:
   - Verifica que el próximo número no exceda el `range_end`
   - Valida que la fecha no exceda `emition_limit`

2. **Al confirmar CAI**:
   - Verifica que la secuencia no tenga otro CAI confirmado
   - Valida que el rango sea válido
   - Comprueba que el establecimiento y punto de emisión existan

3. **Al validar factura**:
   - Extrae el número de la factura
   - Valida contra el rango del CAI
   - Verifica la fecha límite

---

## 📄 Factura DPS

### Características del Reporte

El reporte de factura DPS está diseñado para imprimirse sobre papel pre-impreso con las siguientes características:

- **Formato**: Carta (Letter) vertical
- **Imagen de fondo**: 204mm x 262mm
- **Fuentes**: Poppins Regular y Bold
- **Colores**:
  - Fondo teal oscuro: `#004257`
  - Texto de valores: `#273439`
  - Texto de etiquetas: `#004257`

### Posicionamiento de Elementos

Todos los elementos están posicionados en centímetros para alineación precisa:

| Elemento | Posición |
|----------|----------|
| Datos de la compañía | `top: 0.5cm, right: 0.0cm` |
| Nombre del documento | `top: 3.5cm, right: 9.0cm` |
| Número de documento | `top: 3.8cm, right: 0.0cm` |
| Fecha | `top: 5.0cm, right: 0.0cm` |
| Cliente | `top: 5.5cm, left: 0.5cm` |
| Dirección | `top: 6.0cm, left: 0.5cm, width: 16cm` |
| RTN | `top: 6.0cm, right: 0.0cm` |
| Datos Adquiriente Exonerado | `top: 6.8cm` |
| Tabla de líneas | `top: 8.5cm, max-height: 11.5cm` |
| Footer (totales) | `top: 20.5cm` |
| Número de página | `top: 25.0cm, right: 0.0cm` |

### Uso del Reporte

**Ruta**: `Contabilidad → Clientes → Facturas → [Seleccionar Factura] → Imprimir → Factura DPS`

O desde la factura:
- Botón "Imprimir" → Seleccionar "Factura DPS"

### Personalización

Para personalizar el reporte DPS:

1. **Cambiar imagen de fondo**:
   - Reemplazar `static/src/img/factura_dps_backgroup.png`
   - Mantener el mismo nombre de archivo

2. **Ajustar posiciones**:
   - Editar `report/report_invoice.xml`
   - Modificar valores de `top`, `left`, `right` en los elementos

3. **Cambiar colores**:
   - Buscar y reemplazar códigos de color en el template
   - `#004257`: Color teal oscuro (encabezados)
   - `#273439`: Color de texto de valores

---

## 📊 Libros Fiscales

### Libro de Ventas

#### Generar Libro PDF

**Ruta**: `Contabilidad → Reportes Fiscales de Honduras → Reporte de Registro de Ventas`

1. Seleccionar configuración (se carga automáticamente)
2. Indicar rango de fechas
3. Folio inicial (número de página inicial)
4. Clic en "Generar PDF"

**Características del PDF**:
- Encabezado con RTN de la compañía
- Folio por página
- Incluye facturas en estado `posted` y `cancel`
- Totales por tipo de impuesto al final
- Formato RTN: XXXXX-XXXXXX-X

#### Generar Libro Excel

Mismo proceso, pero seleccionar "Generar Excel".

**Formato XLSX**:
- Mismas columnas que el PDF
- Formato editable
- Listo para importar a sistemas externos

#### Generar PT Libro Ventas

**Ruta**: Mismo wizard, botón "Generar PT Excel"

**Columnas incluidas**:
- Fecha
- Número de documento (con desglose automático)
- RTN Cliente (formateado)
- Nombre Cliente
- Importe Exonerado
- Importe Exento
- Importe Gravado 15%
- Importe Gravado 18%
- ISV 15%
- ISV 18%
- Total
- **Producto**: `[Código cuenta] Nombre de Cuenta` (de `account_id` de cada línea)
- **Condición de Pago**: Términos de pago de la factura

**Validaciones**:
- Cruce de datos entre facturas y asientos contables
- Verificación de totales
- Validación de rangos de números

### Libro de Compras

Proceso similar al libro de ventas, pero desde:
**Ruta**: `Contabilidad → Reportes Fiscales de Honduras → Reporte de Registro de Compras`

**PT Libro Compras incluye**:
- Desglose automático del número de documento desde `ref`
- Comparación ISV declarado vs. asiento contable
- Detalle de debe/haber
- Columnas de observaciones editables

---

## 🔧 Campos Adicionales

### res.partner

| Campo | Tipo | Descripción | Ubicación en Vista |
|-------|------|-------------|-------------------|
| `number_sag_hn` | Char | Número de registro SAG | Pestaña "Categorías" |

**Comportamiento**:
- Se copia automáticamente a las facturas cuando se crea una factura para el partner
- Visible en la sección "Datos Fiscales Honduras" de las facturas

### account.move

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `number_sag_hn` | Char | Número identificativo del registro SAG (heredado del partner) |
| `number_oce_hn` | Char | Correlativo de Orden de Compra Exenta |
| `consecutive_number_oce_hn` | Char | Correlativo de la Constancia del Registro de Exonerados |
| `cai` | Char | Código de Autorización de Impresión (37 caracteres) |
| `emition` | Date | Fecha de recepción del CAI |
| `emition_limit` | Date | Fecha límite de emisión del CAI |
| `range_start_str` | Char | Correlativo inicial del rango autorizado (formateado) |
| `range_end_str` | Char | Correlativo final del rango autorizado (formateado) |
| `declaration` | Char | Declaración fiscal (8 caracteres) |
| `fiscal_document_type_id` | Many2one | Tipo de documento fiscal |
| `l10n_hn_establecimiento_code` | Char | Código de establecimiento (3 dígitos) |
| `l10n_hn_punto_emision_code` | Char | Punto de emisión (3 dígitos) |
| `amount_in_words` | Char | Monto total en letras (calculado) |
| `has_cai` | Boolean | Indica si la factura tiene CAI asignado |

**Vista**: Los campos aparecen en la sección "Datos Fiscales Honduras" en el formulario de factura.

---

## 📁 Estructura del Módulo

```
l10n_hn_fiscal/
├── models/
│   ├── account_move.py              # Campos adicionales, validaciones CAI, métodos DPS
│   ├── account_journal.py           # Extensiones a diarios
│   ├── l10n_hn_cai.py              # Modelo de gestión de CAI
│   ├── l10n_hn_cai_reset_wizard.py # Wizard para restablecer CAI
│   ├── document_type.py            # Tipos de documentos fiscales
│   ├── l10n_hn_fiscal_locations.py # Establecimientos y puntos de emisión
│   ├── ir_sequence.py              # Validaciones y extensiones de secuencias
│   ├── ir_actions_report.py       # Interceptación de reportes
│   ├── res_company.py             # Configuración de reporte por defecto
│   ├── res_config_settings.py     # Ajustes de configuración
│   ├── res_partner.py             # Campo SAG en partners
│   └── sales_report_configuration.py # Configuración de libros
├── report/
│   ├── report_invoice.xml         # Plantilla de factura DPS y factura estándar
│   ├── report_sales_book.xml      # Plantilla libro de ventas PDF
│   ├── report_sales_book.py       # Lógica de procesamiento libro de ventas
│   ├── report_purchase_book.xml   # Plantilla libro de compras PDF
│   └── report_purchase_book.py    # Lógica de procesamiento libro de compras
├── wizard/
│   ├── sales_report_wizard.py     # Wizard para generar libros de ventas
│   ├── sales_report_wizard_view.xml
│   ├── purchase_report_wizard.py  # Wizard para generar libros de compras
│   └── purchase_report_wizard_view.xml
├── views/
│   ├── account_move.xml           # Vista de facturas con campos fiscales
│   ├── account_journal_view.xml   # Extensiones a vista de diarios
│   ├── l10n_hn_cai_view.xml      # Vista de gestión de CAI
│   ├── l10n_hn_cai_wizard_view.xml # Vista wizard restablecer CAI
│   ├── fiscal_document_type_view.xml
│   ├── l10n_hn_fiscal_locations_view.xml
│   ├── ir_sequence.xml            # Vista de secuencias con campos CAI
│   ├── res_partner_view.xml       # Campo SAG en partners
│   ├── sales_report_configuration_view.xml
│   ├── sales_report_menu.xml      # Menús de reportes
│   └── account_config_menu.xml    # Menús de configuración
├── data/
│   ├── fiscal_document_type_data.xml # Tipos de documentos predefinidos
│   ├── report_paperformat_data.xml  # Formatos de papel (Letter, DPS)
│   ├── l10n_hn_chart_data.xml       # Plan de cuentas hondureño
│   ├── account.tax.csv              # Impuestos predefinidos
│   └── ...
├── static/
│   ├── fonts/
│   │   ├── poppins-regular.ttf    # Fuente Poppins Regular
│   │   └── poppins-bold.ttf        # Fuente Poppins Bold
│   ├── src/img/
│   │   ├── factura_dps_backgroup.png # Imagen de fondo DPS
│   │   └── logo_dps_blanco.png      # Logo DPS (no usado actualmente)
│   └── description/
│       ├── index.html              # Página de descripción del módulo
│       └── icon.png                # Icono del módulo
├── utils/
│   └── compat.py                   # Utilidades de compatibilidad Odoo 16/17
├── controllers/
│   └── portal.py                   # Controlador para portal de clientes
├── security/
│   ├── security.xml                # Grupos de seguridad
│   └── ir.model.access.csv         # Permisos de acceso
└── leyes/                          # Documentos legales (PDFs)
    ├── ACUERDO-481-2017.pdf
    ├── ACUERDO-609-2017.pdf
    └── ...
```

---

## 🔄 Flujo de Trabajo Completo

### 1. Configuración Inicial (Una vez)

1. **Datos de la compañía**:
   - Completar RTN en `Ajustes → Contabilidad`
   - (Opcional) Configurar colores corporativos

2. **Establecimientos y Puntos de Emisión**:
   - Crear establecimientos fiscales
   - Crear puntos de emisión para cada establecimiento

3. **Tipos de Documentos Fiscales**:
   - Verificar que existan los tipos necesarios (Factura, Nota de Crédito, etc.)

4. **Configurar Diarios**:
   - Para cada diario de ventas:
     - Marcar "Documento Fiscal" en la secuencia
     - Seleccionar tipo de documento fiscal
     - Configurar prefijo y formato

5. **Crear CAI**:
   - Crear CAI en `Contabilidad → Configuración → CAI`
   - Asociar a diario y secuencia
   - Confirmar CAI

6. **Configurar Libros**:
   - Crear configuración para libro de ventas
   - Crear configuración para libro de compras
   - Seleccionar diarios e impuestos

### 2. Configuración de Partners (Ongoing)

Para cada cliente/proveedor:
- Ir a `Contactos → [Partner] → Pestaña "Categorías"`
- Completar "Número SAG HN"
- Este valor se copiará automáticamente a las facturas

### 3. Emisión de Facturas (Diario)

1. **Crear factura normalmente**:
   - El sistema asigna automáticamente:
     - CAI de la secuencia
     - Datos del rango autorizado
     - Código de establecimiento y punto de emisión
     - Tipo de documento fiscal
     - Número SAG (desde el partner)

2. **Completar datos adicionales** (si aplica):
   - Número de Orden de Compra Exenta (`number_oce_hn`)
   - Correlativo de Constancia de Exonerados (`consecutive_number_oce_hn`)

3. **Validar y Publicar**:
   - El sistema valida:
     - Que el número esté dentro del rango del CAI
     - Que la fecha no exceda la fecha límite
     - Que el CAI esté activo

4. **Imprimir Factura DPS** (si es necesario):
   - Botón "Imprimir" → "Factura DPS"

### 4. Generación de Reportes (Mensual/Trimestral)

#### Libro de Ventas:

1. Ir a `Contabilidad → Reportes Fiscales de Honduras → Reporte de Registro de Ventas`
2. Seleccionar rango de fechas
3. Indicar folio inicial
4. Elegir formato:
   - **PDF**: Para archivo físico
   - **Excel**: Para edición
   - **PT Excel**: Para presentación al SAR

#### Libro de Compras:

Proceso similar desde `Reporte de Registro de Compras`

---

## 🛠️ Troubleshooting

### Problema: El CAI no se asigna a las facturas

**Solución**:
1. Verificar que el CAI esté en estado "Confirmado"
2. Verificar que el CAI esté asociado a la secuencia del diario
3. Verificar que el diario de la factura coincida con el diario del CAI
4. Verificar que la secuencia tenga `active_sar = True`

### Problema: Error "El próximo número excede el rango final del CAI"

**Solución**:
1. Verificar el rango autorizado del CAI
2. Revisar el último número usado en facturas
3. Si es necesario, crear un nuevo CAI con un rango mayor

### Problema: La factura DPS no muestra la imagen de fondo

**Solución**:
1. Verificar que el archivo `static/src/img/factura_dps_backgroup.png` exista
2. Reiniciar el servidor Odoo
3. Actualizar el módulo
4. Verificar permisos de lectura del archivo

### Problema: Los reportes PT no generan correctamente

**Solución**:
1. Verificar que la configuración del libro tenga diarios e impuestos seleccionados
2. Verificar que existan facturas en el rango de fechas seleccionado
3. Revisar los logs del servidor para errores específicos

### Problema: El número SAG no se copia a la factura

**Solución**:
1. Verificar que el campo `number_sag_hn` esté completo en el partner
2. Verificar que la factura esté asociada al partner correcto
3. Si la factura ya existe, el campo se copia al guardar o al cambiar el partner

### Problema: No puedo editar una secuencia con CAI

**Solución**:
1. Esto es normal: las secuencias con CAI confirmado están bloqueadas
2. Para editar: Restablecer el CAI a borrador primero
3. Editar la secuencia
4. Confirmar el CAI nuevamente

---

## 🔒 Seguridad

### Grupos de Seguridad

- **`l10n_hn_fiscal.group_show_l10n_hn_fiscal`**: 
  - Acceso a menús de reportes fiscales
  - Acceso a configuración de CAI
  - Acceso a wizards de libros

### Permisos de Modelos

Los permisos están definidos en `security/ir.model.access.csv`:
- `l10n_hn.cai`: Leer/Escribir para usuarios del grupo
- `sales_report_configuration`: Leer/Escribir para usuarios del grupo
- `sales_report_wizard`: Crear para usuarios del grupo
- `purchase_report_wizard`: Crear para usuarios del grupo

---

## 🔄 Compatibilidad

### Odoo 16
✅ Totalmente compatible

### Odoo 17
✅ Totalmente compatible

El módulo utiliza `utils/compat.py` para manejar diferencias entre versiones:
- Nombres de campos de diarios (`type` vs `journal_type`)
- Nombres de campos de impuestos (`type_tax_use` vs `tax_scope`)
- Modelos de personalización de documentos

---

## 📝 Notas Técnicas

### Formato de Números de Documento

El sistema extrae automáticamente:
- **Establecimiento**: Primeros dígitos del número
- **Punto de Emisión**: Siguientes dígitos
- **Tipo**: Siguientes dígitos
- **Correlativo**: Últimos dígitos

Ejemplo: `001-001-01-00000001` se desglosa en:
- Establecimiento: `001`
- Punto de Emisión: `001`
- Tipo: `01`
- Correlativo: `00000001`

### Formato de RTN

El sistema formatea automáticamente el RTN en formato hondureño:
- Entrada: `08011990123456`
- Salida: `08011-990123-4`

### Cálculo de Totales

Los reportes calculan automáticamente:
- **Importe Exonerado**: Suma de líneas con impuesto EXO
- **Importe Exento**: Suma de líneas con impuesto EXE
- **Importe Gravado 15%**: Suma de líneas con impuesto ISV15
- **Importe Gravado 18%**: Suma de líneas con impuesto ISV18
- **ISV 15%**: 15% del importe gravado 15%
- **ISV 18%**: 18% del importe gravado 18%

### Validación de CAI en Secuencias

Cuando se genera un número de secuencia con `active_sar = True`:
1. Se valida que el próximo número no exceda `range_end`
2. Se valida que la fecha no exceda `emition_limit`
3. Si alguna validación falla, se lanza un `UserError`

---

## 📞 Soporte

**Autor**: Allan Ramirez / INTEGRALL

**Website**: https://www.integrall.solutions

**Precio**: 1,000 EUR

**Licencia**: AGPL-3

---

## 📚 Referencias Legales

El módulo incluye documentación legal en la carpeta `leyes/`:
- ACUERDO-481-2017: Reglamento del Régimen de Facturación
- ACUERDO-609-2017: Modificaciones al régimen
- ACUERDO-817-2018: Actualizaciones
- ACUERDO-231-2020: Normativas recientes

---

## 🎨 Personalización Avanzada

### Modificar Colores del Reporte DPS

Editar `report/report_invoice.xml` y buscar/reemplazar:
- `#004257`: Color teal oscuro (encabezados, etiquetas)
- `#273439`: Color de texto de valores
- `#002734`: Color alternativo para importes

### Ajustar Posiciones de Elementos

Todos los elementos usan `position: absolute` con valores en centímetros. Para ajustar:

1. Abrir `report/report_invoice.xml`
2. Buscar el elemento a ajustar
3. Modificar los valores de `top`, `left`, `right`
4. Guardar y actualizar el módulo

### Agregar Nuevos Campos al Reporte DPS

1. Agregar el campo en `models/account_move.py` si no existe
2. Agregar el campo en la vista `views/account_move.xml`
3. Agregar la visualización en `report/report_invoice.xml` con posición absoluta

---

## 🔍 Validaciones Implementadas

### Validaciones de CAI

- ✅ Rango de números válido
- ✅ Fecha límite no excedida
- ✅ CAI único por secuencia
- ✅ Secuencia bloqueada cuando CAI está confirmado
- ✅ Hash de confirmación para restablecer

### Validaciones de Facturas

- ✅ Número dentro del rango del CAI
- ✅ Fecha dentro del período válido
- ✅ Tipo de documento correcto
- ✅ Propagación automática de datos SAG

### Validaciones de Secuencias

- ✅ No se puede eliminar secuencia con CAI activo
- ✅ No se puede editar secuencia con CAI confirmado
- ✅ Validación de rango antes de generar número

---

## 📈 Mejores Prácticas

1. **Gestión de CAI**:
   - Crear CAI con suficiente rango de números
   - Monitorear números restantes regularmente
   - Renovar CAI antes de que expire

2. **Configuración de Libros**:
   - Crear configuraciones separadas para diferentes períodos si es necesario
   - Documentar qué diarios e impuestos se incluyen en cada libro

3. **Datos de Partners**:
   - Completar números SAG al crear partners
   - Verificar que los datos estén actualizados

4. **Backup**:
   - Realizar backup antes de confirmar CAI
   - Mantener registro de CAI confirmados

---

## 🚨 Limitaciones Conocidas

1. **Factura DPS**: 
   - Requiere papel pre-impreso específico
   - Las posiciones están fijas en centímetros (no responsive)

2. **Reportes PT**:
   - Requieren configuración previa de libros
   - Solo incluyen facturas en estado `posted` y `cancel`

3. **CAI**:
   - Un CAI solo puede estar asociado a una secuencia
   - No se puede tener múltiples CAI activos para la misma secuencia

---

## 📋 Checklist de Configuración

- [ ] Módulo instalado
- [ ] Grupo de seguridad asignado a usuarios
- [ ] RTN de compañía configurado
- [ ] Establecimientos creados
- [ ] Puntos de emisión creados
- [ ] Tipos de documentos fiscales configurados
- [ ] Diarios configurados con secuencias fiscales
- [ ] CAI creados y confirmados
- [ ] Configuración de libro de ventas creada
- [ ] Configuración de libro de compras creada
- [ ] Números SAG completados en partners principales
- [ ] Prueba de factura DPS realizada
- [ ] Prueba de generación de libros realizada

---

## 🔄 Actualizaciones Futuras

El módulo está en constante evolución. Características planificadas:
- Soporte para más formatos de reporte
- Integración con sistemas externos del SAR
- Mejoras en la interfaz de gestión de CAI
- Reportes adicionales según normativa

---

**Versión del módulo**: 16.0.10.0

**Última actualización**: 2024
