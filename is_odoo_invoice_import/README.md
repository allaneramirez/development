# 🧾 Odoo Import Invoice (Integrall Edition)

### Versión / Version: 16.0.2.0  
**Autor / Author:** Allan E. Ramírez Madrid / INTEGRALL  
**Licencia / License:** AGPL-3.0  
**Categoría / Category:** Accounting  
**Compatible con / Compatible with:** Odoo 16 Community & Enterprise  

---

## 🇬🇧 English Description

### 📘 Overview
**Odoo Import Invoice** allows importing **Customer Invoices, Vendor Bills, Credit Notes, and Debit Notes** directly from **Excel files (.xls / .xlsx)** into Odoo Accounting.

It’s designed for accounting departments and consultants who need to migrate or bulk-load invoices efficiently — with full control over journals, currencies, analytic accounts, and account codes.

### 🚀 Key Features
- Import invoices and bills from Excel (.xls / .xlsx)
- Journal and accounting date read from Excel
- Product or Excel-based account mapping
- Auto tax and currency detection
- FEL support (Guatemala): `firma_fel`, `serie_fel`, `numero_fel`
- Analytic distribution: e.g. `Sales:50, Admin:50`
- Downloadable Excel example template
- Validation for headers, dates, and expense types
- Safe transactional import (savepoint rollback)
- Compatible with multi-company context

### 🧭 How to Use
1. Go to **Accounting → Journal Entries → Import Invoices from Excel**
2. Configure import options:
   - Product identification: by code, name, or barcode.
   - Account source: product account or Excel account.
   - Invoice stage: draft or validate automatically.
3. Click **Download Example Template**, fill it with your data.
4. Upload and click **Import Invoices**.

### 🧩 Technical Info
| Component | Description |
|------------|--------------|
| Model | `import.invoice.wizard` |
| Inherited Model | `account.move` (adds URL field) |
| Main File | `wizard/invoice_import.py` |
| Wizard View | `wizard/import_excel_wizard.xml` |
| Access Rules | `security/ir.model.access.csv` |

**Dependencies:** `account`, `xlrd`, `openpyxl`

---

## 🇪🇸 Descripción en Español

### 📘 Descripción General
**Odoo Import Invoice** permite importar **Facturas de Cliente, Facturas de Proveedor, Notas de Crédito y Débito** directamente desde **archivos Excel (.xls / .xlsx)** al módulo de Contabilidad de Odoo.

Está diseñado para departamentos contables y consultores que necesitan migrar o cargar grandes volúmenes de facturas con control total sobre diarios, monedas, cuentas analíticas y códigos contables.

### 🚀 Funcionalidades Clave
- Importa facturas y facturas de proveedor desde Excel (.xls / .xlsx)
- Lee diario y fecha contable desde el archivo
- Usa cuentas desde el producto o definidas en Excel
- Detecta automáticamente impuestos y monedas
- Campos FEL (Guatemala): `firma_fel`, `serie_fel`, `numero_fel`
- Distribución analítica (`Ventas:50, Administración:50`)
- Plantilla de ejemplo descargable
- Validación de encabezados, fechas y tipos de gasto
- Importación segura y transaccional (rollback por savepoint)
- Compatible con multiempresa

### 🧭 Cómo Usarlo
1. Ir a **Contabilidad → Asientos Contables → Importar Facturas desde Excel**
2. Configurar opciones:
   - Identificación de productos: por código, nombre o código de barras.
   - Origen de la cuenta contable: producto o Excel.
   - Estado de las facturas: borrador o validar automáticamente.
3. Descargar la plantilla de ejemplo, llenar datos.
4. Subir el archivo y presionar **Importar Facturas**.

### 🧩 Detalles Técnicos
| Componente | Descripción |
|-------------|-------------|
| Modelo | `import.invoice.wizard` |
| Modelo Heredado | `account.move` (agrega campo URL) |
| Lógica Principal | `wizard/invoice_import.py` |
| Vista del Wizard | `wizard/import_excel_wizard.xml` |
| Seguridad | `security/ir.model.access.csv` |

**Dependencias:** `account`, `xlrd`, `openpyxl`

---

## 🧑‍💻 Credits / Créditos

**Author / Autor:** Allan E. Ramírez Madrid  
**Company / Empresa:** Integrall Solutions  
🌐 Website: [https://integrall.solutions](https://integrall.solutions)  
📧 Email: contact@integrall.solutions  

---

## 🧾 License
This module is released under the **AGPL-3.0** license.  
Este módulo se distribuye bajo la licencia **AGPL-3.0**.  
See / Ver: [https://www.gnu.org/licenses/agpl-3.0.html](https://www.gnu.org/licenses/agpl-3.0.html)
