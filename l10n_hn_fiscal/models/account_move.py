# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import re


class AccountMove(models.Model):
    _inherit = "account.move"

    amount_in_words = fields.Char(string="Monto en letras", readonly=True, compute='get_amount_in_words')
    cai_supplier = fields.Char(string="CAI Supplier", store=True)
    cai = fields.Char(string="CAI", store=True, readonly=True)
    emition = fields.Date('Fecha de recepcion', store=True)
    emition_limit = fields.Date('Fecha limite de emision', store=True)
    declaration = fields.Char('Declaracion', store=True)
    range_start_str = fields.Char('Correlativo Inicial', store=True)
    range_end_str = fields.Char('Correlativo Final', store=True)
    num_contract_exonerated = fields.Char('Constancia resistro exonerada')
    num_contract_sag = fields.Char('Registro SAG')
    num_exempt_purchase = fields.Char('Orden de compra exenta')
    l10n_hn_establecimiento_code = fields.Char(string='Código de Establecimiento', store=True, readonly=True)
    l10n_hn_punto_emision_code = fields.Char(string='Punto de Emisión', store=True, readonly=True)

    def _search_l10n_latam_document_number(self, operator, value):
        """ Search method for l10n_latam_document_number field.
        The search is made on the 'name' field for sales documents and on the 'ref' field for purchase documents.
        """
        if self.env.context.get('journal_type') == 'purchase':
            return [('ref', operator, value)]
        if self.env.context.get('journal_type') == 'sale':
            return [('name', operator, value)]
        # Fallback for other cases or when context is not available
        return ['|', ('name', operator, value), ('ref', operator, value)]

    l10n_latam_document_number = fields.Char(
        string="Número de Documento",
        compute='_compute_l10n_latam_document_number',
        inverse='_inverse_l10n_latam_document_number',
        store=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        search='_search_l10n_latam_document_number',
        help="Para diarios de Venta, es la parte numérica del campo 'Referencia'. "
             "Para diarios de Compra, es el valor completo del campo 'Referencia de Factura de Proveedor'.")

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        if self.journal_id:
            # Search for an active and confirmed CAI for this journal
            cai = self.env['l10n_hn.cai'].search([
                ('journal_id', '=', self.journal_id.id),
                ('state', '=', 'confirmed'),
                ('active', '=', True)
            ], limit=1)

            if cai:
                # A CAI was found, set the document type and restrict the domain
                self.l10n_latam_document_type_id = cai.l10n_latam_document_type_id.id
                domain = {'l10n_latam_document_type_id': [('id', '=', cai.l10n_latam_document_type_id.id)]}
                return {'domain': domain}

        if self.l10n_latam_document_type_id and self.l10n_latam_document_type_id.country_id.code == 'HN':
            self.l10n_latam_document_type_id = False

        domain = {'l10n_latam_document_type_id': [('country_id.code', '=', 'HN')]}
        return {'domain': domain}

    def action_post(self):
        # First, ensure the document number is computed to avoid timing issues with validations.
        self._compute_l10n_latam_document_number()

        for move in self.filtered(
                lambda m: m.company_id.country_id.code == 'HN' and m.journal_id.l10n_latam_use_documents):
            sequence = move.journal_id.sequence_id
            if not (sequence and sequence.active_sar):
                continue

            # 1. Validation: Check if the invoice date is within the CAI's validity period.
            if move.invoice_date and move.invoice_date > sequence.emition_limit:
                raise ValidationError(_(
                    'La fecha de la factura (%s) es posterior a la fecha límite de emisión del CAI (%s).') % (
                                          move.invoice_date, sequence.emition_limit))

            # 2. Validation: Check if the invoice number is within the authorized range.
            if move.name and move.name != '/':
                try:
                    # The compute method has already run, so the value should be up-to-date
                    invoice_number = int(move.l10n_latam_document_number)

                    if not (sequence.range_start <= invoice_number <= sequence.range_end):
                        raise ValidationError(_(
                            'El número de factura (%s) está fuera del rango fiscal autorizado por el CAI (%s - %s).') % (
                                                  invoice_number, sequence.range_start, sequence.range_end))
                except (ValueError, TypeError):
                    raise UserError(_(
                        'No se pudo extraer el número de la factura "%s". El formato no es un número válido para la validación del CAI.') % move.name)

            # 3. Data Population: Enforce document type and copy fiscal data from the sequence to the move.
            move.l10n_latam_document_type_id = sequence.l10n_latam_document_type_id.id
            move.cai = sequence.cai
            move.emition = sequence.emition
            move.emition_limit = sequence.emition_limit
            move.declaration = sequence.declaration
            move.range_end_str = sequence.range_end_str
            move.range_start_str = sequence.range_start_str
            move.l10n_hn_establecimiento_code = sequence.l10n_hn_establecimiento_code
            move.l10n_hn_punto_emision_code = sequence.l10n_hn_punto_emision_code

        return super(AccountMove, self).action_post()

    @api.depends('amount_total')
    def get_amount_in_words(self):
        """ Computes the amount in words for the total. """
        for move in self:
            if move.currency_id:
                move.amount_in_words = move.currency_id.amount_to_text(move.amount_total)
            else:
                move.amount_in_words = ''

#
#    @api.depends('state')
#    def _compute_name(self):
#        for move in self.filtered(lambda m: not m.name and m.state == 'draft'):
#            move.name = '/'
#        return

    @api.depends('name', 'ref', 'journal_id.type')
    def _compute_l10n_latam_document_number(self):
        # ... (lógica de compra sin cambios) ...
        for move in self:
            if move.journal_id.type == 'purchase':
                move.l10n_latam_document_number = move.ref or False
            elif move.journal_id.type == 'sale':
                if move.name and move.name != '/':

                    # --- MODIFICACIÓN AQUÍ ---
                    # Antes: re.sub(r'\D', '', move.name)
                    # Corregido: Extraer solo los dígitos del final
                    match = re.search(r'(\d+)$', move.name)
                    move.l10n_latam_document_number = match.group(1) if match else False
                    # --- FIN DE MODIFICACIÓN ---

                else:
                    move.l10n_latam_document_number = False
            else:
                move.l10n_latam_document_number = False

    def _inverse_l10n_latam_document_number(self):
        """
        Sobreescribe la lógica de l10n_latam_invoice_document para controlar
        manualmente el flujo de datos.
        - Para 'compra', actualiza el campo 'ref'.
        - Para 'venta', no hace NADA para permitir que la secuencia nativa de Odoo controle el campo 'name'.
        """
        for move in self:
            if move.journal_id.type == 'purchase':
                move.l10n_latam_document_number = move.ref
            elif move.journal_id.type == 'sale':
                # No hacer nada. Esto es intencional para anular la sobreescritura
                # del campo 'name' que hace el módulo l10n_latam_invoice_document.
                pass

    def _get_starting_sequence(self):
        """
        Anula la lógica de l10n_latam_invoice_document que ignora la
        configuración de ir.sequence y devuelve un formato 'prefijo 00000000'.
        Al llamar a super() directamente, forzamos que Odoo use la
        lógica nativa, que SÍ lee el 'prefix' y 'padding' de ir.sequence.
        """
        return super(AccountMove, self)._get_starting_sequence()