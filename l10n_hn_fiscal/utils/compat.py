# -*- coding: utf-8 -*-
"""
Utilidades para compatibilidad entre versiones de Odoo (16 y 17).
"""

DEFAULT_PRIMARY_COLOR = '#D3D3D3'


def _get_first_model(env, model_names):
    """Retorna el primer modelo disponible en el entorno."""
    for model_name in model_names:
        if model_name in env:
            return env[model_name]
    return None


def get_company_primary_color(env, company, default=DEFAULT_PRIMARY_COLOR):
    """
    Obtiene el color primario definido en la personalización de documentos.
    Compatible con posibles cambios de modelo entre versiones.
    """
    if not company:
        return default

    layout_model = _get_first_model(env, (
        'base.document.layout',
        'basic.document.layout',
        'company.document.layout',
    ))
    if not layout_model:
        return default

    layout = layout_model.search([('company_id', '=', company.id)], limit=1)
    return layout.primary_color or default


def get_journal_type_field(env):
    """Devuelve el nombre del campo que representa el tipo de diario."""
    journal_model = env['account.journal']
    if 'type' in journal_model._fields:
        return 'type'
    if 'journal_type' in journal_model._fields:
        return 'journal_type'
    return None


def get_journal_type_value(journal):
    """Obtiene el valor del tipo de diario respetando cambios de nombre."""
    if not journal:
        return False
    field_name = get_journal_type_field(journal.env)
    return getattr(journal, field_name, False) if field_name else False


def is_sale_journal(journal):
    return get_journal_type_value(journal) == 'sale'


def is_purchase_journal(journal):
    return get_journal_type_value(journal) == 'purchase'


def make_journal_domain(env, desired_type):
    """Construye un dominio para filtrar diarios por tipo."""
    field_name = get_journal_type_field(env)
    if not field_name:
        return []
    return [(field_name, '=', desired_type)]


def filter_journals_by_type(records, desired_type):
    """Filtra recordsets de diarios por tipo."""
    if not records:
        return records
    field_name = get_journal_type_field(records.env)
    if not field_name:
        return records
    return records.filtered(lambda journal: getattr(journal, field_name) == desired_type)


def get_tax_scope_field(env):
    """Devuelve el campo que indica si un impuesto aplica a ventas o compras."""
    tax_model = env['account.tax']
    if 'type_tax_use' in tax_model._fields:
        return 'type_tax_use'
    if 'tax_scope' in tax_model._fields:
        return 'tax_scope'
    return None


def make_tax_domain(env, desired_scope):
    """Construye un dominio para filtrar impuestos por scope."""
    field_name = get_tax_scope_field(env)
    if not field_name:
        return []
    if desired_scope == 'both':
        return [(field_name, 'in', ['sale', 'purchase'])]
    return [(field_name, '=', desired_scope)]


def filter_taxes_by_scope(records, desired_scope):
    """Filtra impuestos según su alcance (venta/compra)."""
    if not records:
        return records
    field_name = get_tax_scope_field(records.env)
    if not field_name:
        return records
    if desired_scope == 'both':
        return records.filtered(lambda tax: getattr(tax, field_name) in ('sale', 'purchase'))
    return records.filtered(lambda tax: getattr(tax, field_name) == desired_scope)

