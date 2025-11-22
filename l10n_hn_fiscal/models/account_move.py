# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import re


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
    number_sag_hn = fields.Char('Número de Registro SAG', oldname='num_contract_sag')
    number_oce_hn = fields.Char('Número OCE HN', oldname='num_exempt_purchase')
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

            if cai:
                # A CAI was found, use its document type (highest priority)
                fiscal_document_type_id = cai.fiscal_document_type_id.id
                has_cai_or_sequence = True
            else:
                # Priority 2: If no CAI found, search in the sequence
                # Check if the journal has a sequence with CAI and fiscal_document_type
                sequence = self.journal_id.sequence_id
                if sequence and sequence.cai and sequence.fiscal_document_type_id:
                    # Sequence has CAI and document type, use it
                    fiscal_document_type_id = sequence.fiscal_document_type_id.id
                    has_cai_or_sequence = True

            if has_cai_or_sequence and fiscal_document_type_id:
                # Set the document type and restrict the domain only if there's CAI or sequence with CAI
                self.fiscal_document_type_id = fiscal_document_type_id
                domain = {'fiscal_document_type_id': [('id', '=', fiscal_document_type_id)]}
                return {'domain': domain}
            else:
                # No CAI or sequence with CAI found, or CAI/sequence found but no document type
                # Allow selection of any document type from the same country as the company
                company_country = self.company_id.country_id
                if company_country:
                    # Clear the document type if it's from a different country
                    if self.fiscal_document_type_id and self.fiscal_document_type_id.country_id.id != company_country.id:
                        self.fiscal_document_type_id = False
                    # Allow selection of any document type from the company's country
                    domain = {'fiscal_document_type_id': [('country_id', '=', company_country.id)]}
                    return {'domain': domain}
                else:
                    # No country set for company, allow free selection
                    if self.fiscal_document_type_id:
                        self.fiscal_document_type_id = False
                    return {'domain': {'fiscal_document_type_id': []}}
        else:
            # If no journal selected, restrict to company's country if available
            company_country = self.company_id.country_id
            if company_country:
                # Clear the document type if it's from a different country
                if self.fiscal_document_type_id and self.fiscal_document_type_id.country_id.id != company_country.id:
                    self.fiscal_document_type_id = False
                # Allow selection of any document type from the company's country
                domain = {'fiscal_document_type_id': [('country_id', '=', company_country.id)]}
                return {'domain': domain}
            else:
                # No country set for company, allow free selection
                if self.fiscal_document_type_id:
                    self.fiscal_document_type_id = False
                return {'domain': {'fiscal_document_type_id': []}}

    def action_post(self):

        for move in self.filtered(
                lambda m: m.company_id.country_id.code == 'HN'):
            sequence = move.journal_id.sequence_id
            
            if not (sequence and sequence.active_sar):
                continue

            # 1. Validation: Check if the invoice date is within the CAI's validity period.
            if move.invoice_date and move.invoice_date > sequence.emition_limit:
                raise ValidationError(_(
                    'La fecha de la factura (%s) es posterior a la fecha límite para emisión del CAI (%s).') % (
                                          move.invoice_date, sequence.emition_limit))

            # 2. Validation: Check if the invoice number is within the authorized range.
            if move.name and move.name != '/':
                try:
                    match = re.search(r'(\d+)$', move.name)
                    if not match:
                        raise UserError(_('No se pudo extraer la parte numérica del número de factura "%s" para la validación del CAI.') % move.name)
                    
                    invoice_number = int(match.group(1))

                    if not (sequence.range_start <= invoice_number <= sequence.range_end):
                        raise ValidationError(_(
                            'El número de factura (%s) está fuera del rango fiscal autorizado por el CAI (%s - %s).') % (
                                                  invoice_number, sequence.range_start, sequence.range_end))
                except (ValueError, TypeError):
                    raise UserError(_(
                        'No se pudo extraer el número de la factura "%s". El formato no es un número válido para la validación del CAI.') % move.name)

            # 3. Data Population: Enforce document type and copy fiscal data from the sequence to the move.
            move.fiscal_document_type_id = sequence.fiscal_document_type_id.id
            move.cai = sequence.cai
            move.emition = sequence.emition
            move.emition_limit = sequence.emition_limit
            move.declaration = sequence.declaration
            move.range_end_str = sequence.range_end_str
            move.range_start_str = sequence.range_start_str
            move.l10n_hn_establecimiento_code = sequence.l10n_hn_establecimiento_code
            move.l10n_hn_punto_emision_code = sequence.l10n_hn_punto_emision_code

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
            self.journal_id.type == 'sale' and 
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