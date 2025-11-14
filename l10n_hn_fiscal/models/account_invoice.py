# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

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

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        """
        When the journal changes, find the active CAI configuration for it.
        If found, it sets the document type on the invoice to the one specified in the CAI
        and applies a domain to restrict the selection to only that document type.
        """
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

        # If no journal or no active CAI, reset the document type if it was a HN one
        # and reset the domain to allow any HN document type.
        if self.l10n_latam_document_type_id and self.l10n_latam_document_type_id.country_id.code == 'HN':
            self.l10n_latam_document_type_id = False
        
        domain = {'l10n_latam_document_type_id': [('country_id.code', '=', 'HN')]}
        return {'domain': domain}

    def action_post(self):
        """
        Extends the posting process to include Honduran fiscal validations.
        This method validates the CAI's expiration date and number range for each invoice
        and copies the fiscal data from the sequence to the invoice itself.
        Improvements:
        - Iterates over each move in the recordset.
        - Uses ValidationError for cleaner error messages.
        - Implements a more robust check for the fiscal number range.
        - Removes unsafe sequence decrements on validation failure.
        """
        for move in self.filtered(lambda m: m.company_id.country_id.code == 'HN' and m.journal_id.l10n_latam_use_documents):
            sequence = move.journal_id.sequence_id
            if not (sequence and sequence.active_sar):
                continue

            # 1. Validation: Check if the invoice date is within the CAI's validity period.
            if move.invoice_date and move.invoice_date > sequence.emition_limit:
                raise ValidationError(_(
                    'La fecha de la factura (%s) es posterior a la fecha límite de emisión del CAI (%s).') % (
                    move.invoice_date, sequence.emition_limit))

            # 2. Validation: Check if the invoice number is within the authorized range.
            # The invoice number is expected to be in the format 'XXX-XXX-XX-NNNNNNNN'
            # We extract the final numeric part for validation.
            if move.name and move.name != '/':
                try:
                    # Extracts the numeric part of the sequence from the move name.
                    # l10n_latam_document_number already provides the plain number.
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

        return super(AccountMove, self).action_post()

    @api.depends('amount_total')
    def get_amount_in_words(self):
        """ Computes the amount in words for the total. """
        for move in self:
            if move.currency_id:
                move.amount_in_words = move.currency_id.amount_to_text(move.amount_total)
            else:
                move.amount_in_words = ''