# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from ..utils import compat
import re
import os
import base64


class AccountMove(models.Model):
    _inherit = "account.move"

    amount_in_words = fields.Char(string="Monto en letras", readonly=True, compute='get_amount_in_words', store=False)
    cai_supplier = fields.Char(string="CAI Supplier", store=True)
    cai = fields.Char(string="CAI", store=True, readonly=True)
    emition = fields.Date('Fecha de recepcion', store=True)
    emition_limit = fields.Date('Fecha limite de emision', store=True)
    declaration = fields.Char('Declaracion', store=True)
    range_start_str = fields.Char('Correlativo Inicial', store=True)
    range_end_str = fields.Char('Correlativo Final', store=True)
    number_sag_hn = fields.Char('Número Identificativo del Registro SAG', oldname='num_contract_sag')
    number_oce_hn = fields.Char('Correlativo Orden de Compra Exenta', oldname='num_exempt_purchase')
    consecutive_number_oce_hn = fields.Char('Correlativo de la Constancia del Registro de Exonerados')
    l10n_hn_establecimiento_code = fields.Char(string='Código de Establecimiento', store=True, readonly=True)
    l10n_hn_punto_emision_code = fields.Char(string='Punto de Emisión', store=True, readonly=True)
    fiscal_document_type_id = fields.Many2one(
        comodel_name="fiscal_document_type",
        store=True,
        string="Tipo de documento"
    )
    
    has_cai = fields.Boolean(
        string='Tiene CAI',
        compute='_compute_has_cai',
        store=False,
        help="Indica si la factura tiene un CAI asignado. Campo auxiliar para restricciones de vista."
    )
    
    @api.depends('cai')
    def _compute_has_cai(self):
        """Calcula si la factura tiene un CAI asignado."""
        for move in self:
            move.has_cai = bool(move.cai)

    def _sync_partner_sag_value(self, vals):
        """Propaga el número SAG desde el partner si no fue establecido manualmente."""
        partner_id = vals.get('partner_id')
        if partner_id is not None and 'number_sag_hn' not in vals:
            partner = self.env['res.partner'].browse(partner_id)
            vals = dict(vals)
            vals['number_sag_hn'] = partner.number_sag_hn or False
        return vals

    @api.model
    def create(self, vals):
        vals = self._sync_partner_sag_value(vals)
        return super().create(vals)

    def write(self, vals):
        if 'partner_id' in vals and 'number_sag_hn' not in vals:
            vals = self._sync_partner_sag_value(vals)
        return super().write(vals)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        res = super()._onchange_partner_id()
        if self.partner_id:
            self.number_sag_hn = self.partner_id.number_sag_hn or False
        else:
            self.number_sag_hn = False
        return res

    @api.constrains('move_type', 'fiscal_document_type_id')
    def _check_fiscal_document_type(self):
        """
        Valida que el tipo de documento fiscal sea compatible con el tipo de movimiento.
        - No se puede usar un documento tipo 'invoice' o 'debit_note' con un movimiento tipo 'refund'
        - No se puede usar un documento tipo 'credit_note' con un movimiento tipo 'invoice'
        Solo se ejecuta si la compañía es de Honduras.
        """
        for rec in self:
            # Solo validar si la compañía es de Honduras
            company_country = rec.company_id.country_id if rec.company_id else False
            if not company_country or company_country.code != 'HN':
                continue
            
            if not rec.fiscal_document_type_id or not rec.fiscal_document_type_id.internal_type:
                # Si no hay tipo de documento o no tiene internal_type, no validar
                continue

            internal_type = rec.fiscal_document_type_id.internal_type
            move_type = rec.move_type

            # Validar que no se use invoice/debit_note con refund
            if internal_type in ['invoice', 'debit_note'] and move_type in ['out_refund', 'in_refund']:
                raise ValidationError(_(
                    'No se puede usar un tipo de documento "%s" con una nota de crédito/reembolso. '
                    'Por favor, seleccione un tipo de documento de nota de crédito.'
                ) % rec.fiscal_document_type_id.name)

            # Validar que no se use credit_note con invoice
            elif internal_type == 'credit_note' and move_type in ['out_invoice', 'in_invoice']:
                raise ValidationError(_(
                    'No se puede usar un tipo de documento "%s" con una factura. '
                    'Por favor, seleccione un tipo de documento de factura o nota de débito.'
                ) % rec.fiscal_document_type_id.name)

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        if self.journal_id:
            fiscal_document_type_id = False
            has_cai_or_sequence = False
            
            # Priority 1: Search for an active and confirmed CAI for this journal
            cai = self.env['l10n_hn.cai'].search([
                ('journal_id', '=', self.journal_id.id),
                ('state', '=', 'confirmed'),
                ('active', '=', True)
            ], limit=1)

            if cai and cai.fiscal_document_type_id:
                # A CAI was found with document type, use it (highest priority)
                fiscal_document_type_id = cai.fiscal_document_type_id.id
                has_cai_or_sequence = True
            else:
                # Priority 2: If no CAI found, check in the sequence
                sequence = self.journal_id.sequence_id
                if sequence and sequence.active_sar and sequence.fiscal_document_type_id:
                    # Sequence has fiscal_document_type_id, use it
                    fiscal_document_type_id = sequence.fiscal_document_type_id.id
                    has_cai_or_sequence = True

            if has_cai_or_sequence and fiscal_document_type_id:
                # Set the document type and restrict the domain only if there's CAI or sequence with document type
                self.fiscal_document_type_id = fiscal_document_type_id
                domain = {'fiscal_document_type_id': [('id', '=', fiscal_document_type_id)]}
                return {'domain': domain}
            else:
                # No CAI or sequence with document type found
                # Allow selection of any document type from the same country as the company
                # DO NOT clear the existing value - let user keep their selection
                company_country = self.company_id.country_id
                if company_country:
                    # Only clear if it's from a different country
                    if self.fiscal_document_type_id and self.fiscal_document_type_id.country_id.id != company_country.id:
                        self.fiscal_document_type_id = False
                    # Allow selection of any document type from the company's country
                    domain = {'fiscal_document_type_id': [('country_id', '=', company_country.id)]}
                    return {'domain': domain}
                else:
                    # No country set for company, allow free selection
                    # Don't clear existing value
                    return {'domain': {'fiscal_document_type_id': []}}
        else:
            # If no journal selected, restrict to company's country if available
            company_country = self.company_id.country_id
            if company_country:
                # Only clear if it's from a different country
                if self.fiscal_document_type_id and self.fiscal_document_type_id.country_id.id != company_country.id:
                    self.fiscal_document_type_id = False
                # Allow selection of any document type from the company's country
                domain = {'fiscal_document_type_id': [('country_id', '=', company_country.id)]}
                return {'domain': domain}
            else:
                # No country set for company, allow free selection
                # Don't clear existing value
                return {'domain': {'fiscal_document_type_id': []}}

    def action_post(self):

        for move in self.filtered(
                lambda m: m.company_id.country_id.code == 'HN'):
            sequence = move.journal_id.sequence_id
            
            if not (sequence and sequence.active_sar):
                continue

            # Priority 1: Check if there's a confirmed CAI for this journal
            # This takes precedence over the sequence's fiscal_document_type_id
            cai = self.env['l10n_hn.cai'].search([
                ('journal_id', '=', move.journal_id.id),
                ('state', '=', 'confirmed'),
                ('active', '=', True)
            ], limit=1)

            # 1. Validation: Check if the invoice date is within the CAI's validity period.
            # Use CAI's emition_limit if available, otherwise use sequence's
            emition_limit = cai.emition_limit if cai else sequence.emition_limit
            if move.invoice_date and emition_limit and move.invoice_date > emition_limit:
                raise ValidationError(_(
                    'La fecha de la factura (%s) es posterior a la fecha límite para emisión del CAI (%s).') % (
                                          move.invoice_date, emition_limit))

            # 2. Validation: Check if the invoice number is within the authorized range.
            # Use CAI's range if available, otherwise use sequence's
            range_start = cai.range_start if cai else sequence.range_start
            range_end = cai.range_end if cai else sequence.range_end
            if move.name and move.name != '/':
                try:
                    match = re.search(r'(\d+)$', move.name)
                    if not match:
                        raise UserError(_('No se pudo extraer la parte numérica del número de factura "%s" para la validación del CAI.') % move.name)
                    
                    invoice_number = int(match.group(1))

                    if range_start and range_end and not (range_start <= invoice_number <= range_end):
                        raise ValidationError(_(
                            'El número de factura (%s) está fuera del rango fiscal autorizado por el CAI (%s - %s).') % (
                                                  invoice_number, range_start, range_end))
                except (ValueError, TypeError):
                    raise UserError(_(
                        'No se pudo extraer el número de la factura "%s". El formato no es un número válido para la validación del CAI.') % move.name)

            # 3. Data Population: Copy fiscal data from CAI (priority) or sequence to the move.
            # Only override fiscal_document_type_id if there's a valid value from CAI or sequence
            if cai and cai.fiscal_document_type_id:
                # Priority 1: Use CAI's fiscal_document_type_id if available
                # When CAI is confirmed, it updates the sequence, so we can use sequence values
                # for range_start_str and range_end_str
                move.fiscal_document_type_id = cai.fiscal_document_type_id.id
                move.cai = cai.name
                move.emition = cai.emition
                move.emition_limit = cai.emition_limit
                move.declaration = cai.declaration
                move.range_end_str = sequence.range_end_str
                move.range_start_str = sequence.range_start_str
                move.l10n_hn_establecimiento_code = cai.establecimiento_id.code if cai.establecimiento_id else False
                move.l10n_hn_punto_emision_code = cai.punto_emision_id.code if cai.punto_emision_id else False
            elif sequence.fiscal_document_type_id:
                # Priority 2: Use sequence's fiscal_document_type_id if available and no CAI
                move.fiscal_document_type_id = sequence.fiscal_document_type_id.id
                move.cai = sequence.cai
                move.emition = sequence.emition
                move.emition_limit = sequence.emition_limit
                move.declaration = sequence.declaration
                move.range_end_str = sequence.range_end_str
                move.range_start_str = sequence.range_start_str
                move.l10n_hn_establecimiento_code = sequence.l10n_hn_establecimiento_code
                move.l10n_hn_punto_emision_code = sequence.l10n_hn_punto_emision_code
            else:
                # Priority 3: No CAI and sequence has no fiscal_document_type_id
                # Keep the user-selected fiscal_document_type_id (don't override)
                # Only copy other fiscal data if available in sequence
                if sequence.cai:
                    move.cai = sequence.cai
                if sequence.emition:
                    move.emition = sequence.emition
                if sequence.emition_limit:
                    move.emition_limit = sequence.emition_limit
                if sequence.declaration:
                    move.declaration = sequence.declaration
                if sequence.range_end_str:
                    move.range_end_str = sequence.range_end_str
                if sequence.range_start_str:
                    move.range_start_str = sequence.range_start_str
                if sequence.l10n_hn_establecimiento_code:
                    move.l10n_hn_establecimiento_code = sequence.l10n_hn_establecimiento_code
                if sequence.l10n_hn_punto_emision_code:
                    move.l10n_hn_punto_emision_code = sequence.l10n_hn_punto_emision_code
                # fiscal_document_type_id is NOT overridden - keep user's selection

        return super(AccountMove, self).action_post()

    @api.depends('amount_total', 'currency_id')
    def get_amount_in_words(self):
        """ Computes the amount in words for the total. """
        for move in self:
            if move.currency_id:
                move.amount_in_words = move.currency_id.amount_to_text(move.amount_total)
            else:
                move.amount_in_words = ''

    def action_invoice_sent(self):
        """
        El método action_invoice_sent() no necesita ser sobrescrito porque
        el reporte personalizado se maneja en mail.template.generate_email()
        """
        return super().action_invoice_sent()

    def _get_report_base_filename(self):
        """
        Sobrescribe el método para usar el reporte personalizado cuando se imprime
        una factura de venta.
        """
        self.ensure_one()
        return super()._get_report_base_filename()

    def action_print(self):
        """
        Sobrescribe el método para usar el reporte personalizado cuando se imprime
        una factura de venta. Este método se llama cuando se hace clic en "Imprimir".
        Nota: La interceptación principal se hace en ir_actions_report.py, pero este método
        puede ser llamado desde algunos lugares específicos.
        """
        self.ensure_one()
        # Verificar si es una factura de venta y si hay un reporte personalizado configurado
        if (self.move_type == 'out_invoice' and 
            compat.is_sale_journal(self.journal_id) and 
            self.company_id.out_invoice_report_to_print):
            # Usar el reporte personalizado configurado
            return self.company_id.out_invoice_report_to_print.report_action(self)
        # Si no cumple las condiciones, retornar None ya que action_print puede no existir
        # en el modelo base de Odoo 16. La interceptación principal se hace en ir_actions_report.py
        return None

    def preview_invoice(self):
        """
        Sobrescribe el método para mostrar la vista del portal.
        El reporte personalizado se maneja en el controlador del portal.
        """
        # No necesitamos cambiar nada aquí, el comportamiento por defecto
        # abre la vista del portal, y el controlador del portal ya maneja
        # el reporte personalizado cuando se descarga el PDF
        # Intentar llamar al método padre si existe, sino usar el comportamiento por defecto
        try:
            return super().preview_invoice()
        except AttributeError:
            # Si no existe el método en el padre, redirigir al portal manualmente
            return {
                'type': 'ir.actions.act_url',
                'url': '/my/invoices/%s' % self.id,
                'target': 'self',
            }
    
    def _get_static_image(self, filename):
        """Método helper para cargar imágenes estáticas como base64."""
        try:
            # Obtener la ruta del módulo desde el archivo actual
            current_file = os.path.abspath(__file__)
            # Ir desde models/account_move.py -> l10n_hn_fiscal/ -> static/description/
            module_dir = os.path.dirname(os.path.dirname(current_file))
            image_path = os.path.join(module_dir, 'static', 'src', 'img', filename)
            
            if os.path.exists(image_path):
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                    return base64.b64encode(image_data).decode('utf-8')
            
            # Fallback: intentar con addons_path
            import odoo
            addons_paths = odoo.tools.config.get('addons_path', '').split(',')
            for addons_path in addons_paths:
                addons_path = addons_path.strip()
                image_path = os.path.join(addons_path, 'l10n_hn_fiscal', 'static', 'src', 'img', filename)
                if os.path.exists(image_path):
                    with open(image_path, 'rb') as f:
                        image_data = f.read()
                        return base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.warning("Error loading image %s: %s", filename, str(e))
        return None
    
    def get_dps_background_image(self):
        """Carga la imagen de fondo de la factura DPS como base64."""
        return self._get_static_image('factura_dps_backgroup.png')
    
    def get_dps_logo_image(self):
        """Carga el logo DPS blanco como base64."""
        return self._get_static_image('logo_dps_blanco.png')
    
    def _get_static_font(self, filename):
        """Helper para cargar una fuente estática como base64."""
        try:
            current_file = os.path.abspath(__file__)
            module_path = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
            font_path = os.path.join(module_path, 'l10n_hn_fiscal', 'static', 'fonts', filename)
            if os.path.exists(font_path):
                with open(font_path, 'rb') as f:
                    font_data = f.read()
                    return base64.b64encode(font_data).decode('utf-8')
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.warning("Error loading font %s: %s", filename, str(e))
        return None
    
    def get_poppins_regular_font(self):
        """Carga la fuente Poppins Regular como base64."""
        return self._get_static_font('poppins-regular.ttf')
    
    def get_poppins_bold_font(self):
        """Carga la fuente Poppins Bold como base64."""
        return self._get_static_font('poppins-bold.ttf')
    
    def get_document_name_dps(self):
        """Obtiene el nombre del documento para el reporte DPS, deduciéndolo si es necesario."""
        # Caso especial: Nota de Débito cuando move_type es out_invoice y fiscal_document_type_id es debit_note
        if self.move_type == 'out_invoice' and self.fiscal_document_type_id and self.fiscal_document_type_id.internal_type == 'debit_note':
            return 'NOTA DE DÉBITO'
        
        # Si existe fiscal_document_type_id y no es el caso anterior, usar su nombre
        if self.fiscal_document_type_id:
            return (self.fiscal_document_type_id.name or '').upper()
        
        # Si no existe fiscal_document_type_id, deducir según move_type y state
        if self.move_type == 'out_invoice' and self.state == 'posted':
            return 'FACTURA'
        if self.move_type == 'out_invoice' and self.state == 'draft':
            return 'FACTURA BORRADOR'
        if self.move_type == 'out_refund':
            return 'NOTA DE CRÉDITO'
        
        # Fallback
        return 'FACTURA'
    
    def get_formatted_date_dps(self):
        """Obtiene la fecha formateada en español para el reporte DPS: 'día de mes de año'."""
        if not self.invoice_date:
            return ''
        
        month_names = {
            '01': 'enero', '02': 'febrero', '03': 'marzo', '04': 'abril',
            '05': 'mayo', '06': 'junio', '07': 'julio', '08': 'agosto',
            '09': 'septiembre', '10': 'octubre', '11': 'noviembre', '12': 'diciembre'
        }
        
        day = self.invoice_date.strftime('%d')
        month = self.invoice_date.strftime('%m')
        year = self.invoice_date.strftime('%Y')
        month_name = month_names.get(month, month)
        
        return f"{day} de {month_name} de {year}"