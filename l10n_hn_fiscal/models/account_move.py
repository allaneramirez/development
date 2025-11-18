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
    fiscal_document_type_id = fields.Many2one(
        comodel_name="fiscal_document_type",
        store=True,
        string="Tipo de documento"
    )

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
                self.fiscal_document_type_id = cai.fiscal_document_type_id.id
                domain = {'fiscal_document_type_id': [('id', '=', cai.fiscal_document_type_id.id)]}
                return {'domain': domain}

        if self.fiscal_document_type_id and self.fiscal_document_type_id.country_id.code == 'HN':
            self.fiscal_document_type_id = False

        domain = {'fiscal_document_type_id': [('country_id.code', '=', 'HN')]}
        return {'domain': domain}

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

    @api.depends('amount_total')
    def get_amount_in_words(self):
        """ Computes the amount in words for the total. """
        for move in self:
            if move.currency_id:
                move.amount_in_words = move.currency_id.amount_to_text(move.amount_total)
            else:
                move.amount_in_words = ''