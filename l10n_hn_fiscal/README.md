# Facturación SAR (Honduras)

Módulo para Odoo 16 que centraliza las obligaciones fiscales Hondureñas:

- Control de CAI, tipos de documentos fiscales y secuencias.
- Configuración de libros de ventas y compras con filtros por impuestos/diarios.
- Libros PDF y Excel (Registro y PT) para ventas y compras con desglose por impuesto.
- Campos adicionales en `res.partner` y `account.move` para cumplir con los requisitos del SAR.

## 1. Configuración Inicial

### 1.1. Habilitar el módulo

1. Ve a **Aplicaciones** y busca “Facturación SAR”.
2. Instala el módulo y activa el grupo de seguridad `l10n_hn_fiscal.group_show_l10n_hn_fiscal` para los usuarios que gestionarán la información fiscal.

### 1.2. Datos fiscales de la compañía

En **Ajustes → Contabilidad**, completa:

- CAI y rangos autorizados.
- Colores corporativos (usados en los reportes).
- Identificación fiscal (RTN).

### 1.3. Configurar tipos de documentos

En **Contabilidad → Configuración → Documentos Fiscales HN** define los tipos admitidos por el SAR. Cada tipo puede utilizarse en diarios y secuencias con CAI.

## 2. Campos adicionales

| Modelo | Campo | Descripción |
|--------|-------|-------------|
| `res.partner` | `number_sag_hn` | Número de registro SAG (visible bajo Categorías). |
| `account.move` | `number_sag_hn`, `number_oce_hn` | Heredados del partner y usados en reportes. |
| `account.move` | `archivo`/`name` (wizard) | Propaga los archivos y nombres generados en los reportes. |

## 3. Configuración de Libros

### 3.1. Registro de Ventas / Compras

1. Navega a **Contabilidad → Configuración → Configuración de Registro de Compras y Ventas**.
2. Crea un registro para **Ventas** y otro para **Compras**:
   - Selecciona el tipo de reporte (ventas o compras).
   - Escoge los diarios permitidos (solo se muestran los del tipo correspondiente).
   - Selecciona los impuestos habilitados para el libro.
3. Utiliza los botones laterales para abrir el **Wizard** del libro según corresponda.

## 4. Uso de los Reportes

### 4.1. Wizard de Ventas

1. Ir a **Contabilidad → Reportes Fiscales de Honduras → Reporte de Registro de Ventas**.
2. Seleccionar fechas y folio inicial.
3. Botones disponibles:
   - **Generar PDF**: Libro tradicional.
   - **Generar Excel**: Versión XLSX del registro.
   - **Generar PT Excel**: Libro PT con validaciones cruzadas, incluye:
     - Importe gravado e ISV por tasa (15% y 18%).
     - Número de documento, establecimiento, punto de emisión y correlativo.
     - Detalle del asiento contable (Debe/Haber) y columnas de observaciones.
     - Condición de pago.

### 4.2. Wizard de Compras

Mismos pasos que ventas pero desde **Reporte de Registro de Compras**. El PT Libro Compras añade:

- Columnas derivadas de `ref` (Establecimiento, Punto de Emisión, Tipo y Correlativo).
- Comparación del ISV declarado vs. asiento contable.
- Detalle de debe/haber y observaciones editables.

## 5. Reportes PDF

- Ambos libros (ventas/compras) heredan de `report_sales_book` y `report_purchase_book` respectivamente.
- Incluyen:
  - Encabezado compacto con RTN.
  - Folio por página.
  - Documentos `posted` y `cancel`.
  - Totales por tipo de impuesto.

## 6. Accesos y Seguridad

- Los reportes y menús están protegidos por el grupo `l10n_hn_fiscal.group_show_l10n_hn_fiscal`.
- Los wizards cuentan con permisos específicos en `security/ir.model.access.csv`.

## 7. Archivos clave

| Ruta | Descripción |
|------|-------------|
| `models/account_move.py` | Campos extra (SAG, OCE, etc.) y propagación desde el partner. |
| `views/account_move.xml` | Sección “Datos Fiscales Honduras” con los nuevos campos. |
| `wizard/sales_report_wizard*.py/xml` | Wizards de libros de ventas. |
| `wizard/purchase_report_wizard*.py/xml` | Wizards de libros de compras. |
| `report/report_*_book.py/xml` | Plantillas y lógica de PDF para libros. |

## 8. Flujo típico

1. Completar datos de compañía y CAI.
2. Configurar documentos fiscales y diarios.
3. Asignar números SAG/OCE a los clientes/proveedores.
4. Configurar libros (ventas/compras).
5. Ejecutar los wizards según sea necesario (PDF, Excel o PT).

