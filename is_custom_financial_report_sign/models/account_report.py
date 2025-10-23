# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.misc import get_lang
import babel.dates
import logging

_logger = logging.getLogger(__name__)

class AccountReport(models.Model):
    _inherit = 'account.report'

    show_sign_area = fields.Boolean(
        string="Show Sign Area",
        compute='_compute_show_sign_area'
    )

    def _compute_show_sign_area(self):
        # Asegúrate que 'account_reports.balance_sheet' sea el ID correcto
        financial_report = self.env.ref('account_reports.balance_sheet', raise_if_not_found=False)
        profit_and_loss = self.env.ref('account_reports.profit_and_loss', raise_if_not_found=False)

        for report in self:
            report_id = report.id
            is_financial_report = financial_report and report_id == financial_report.id
            is_profit_and_loss = profit_and_loss and report_id == profit_and_loss.id
            report.show_sign_area = is_financial_report or is_profit_and_loss

    def _format_date_es(self, date_obj):
        if not date_obj: return ''
        lang_code = 'es_GT' if 'es_GT' in self.env['res.lang'].get_installed() else 'es'
        try:
            formatted_date = babel.dates.format_date(date_obj, format='d MMMM y', locale=lang_code)
            parts = formatted_date.split(' ')
            if len(parts) == 3: return f"{parts[0]} de {parts[1]} de {parts[2]}"
            return formatted_date
        except Exception as e:
            _logger.error(f"Error formateando fecha {date_obj} con locale {lang_code}: {e}")
            try: return date_obj.strftime('%d de %B de %Y')
            except: return date_obj.strftime('%d/%m/%Y')

    def _get_report_rendering_context(self, options):
        """Prepara el contexto solo con nuestras variables personalizadas."""
        company = self.env.company
        report_name = self.name
        date_options = options.get('date', {})
        date_from_str = date_options.get('date_from')
        date_to_str = date_options.get('date_to')
        date_from = fields.Date.from_string(date_from_str) if date_from_str else None
        date_to = fields.Date.from_string(date_to_str) if date_to_str else None
        date_range_es = "Periodo no especificado"
        if date_from and date_to: date_range_es = f"Del {self._format_date_es(date_from)} al {self._format_date_es(date_to)}"
        elif date_to: date_range_es = f"Al {self._format_date_es(date_to)}"
        currency_name = company.currency_id.full_name or 'Moneda no especificada'
        currency_es = f"(Expresado en {currency_name})"
        render_context = {
            'company_name': company.name or '',
            'company_vat': company.vat or '',
            'report_name': report_name or '',  # Nombre para nuestro encabezado
            'date_range_es': date_range_es,
            'currency_es': currency_es,
            'report': self,
            'data': self.env.company if self.show_sign_area else None,
            'options': options,
            'env': self.env,
            'report_company_name': company.display_name,
            # Añadir report_title para la parte 't-else' del XML
            'report_title': self.name,
        }
        return render_context

    # *** Usamos get_html para pasar el contexto de forma segura ANTES de super() ***
    def get_html(self, options, *args, **kwargs):
        # 1. Preparar nuestro contexto adicional
        local_context = self._get_report_rendering_context(options)

        # 2. Obtener el contexto adicional existente y fusionarlo
        original_additional_context = kwargs.get('additional_context', {})
        merged_additional_context = original_additional_context.copy()
        # Damos prioridad a nuestras variables si hay colisión
        merged_additional_context.update(local_context)

        # 3. Actualizar kwargs con el contexto fusionado
        kwargs['additional_context'] = merged_additional_context

        # 4. Llamar a super() pasando el contexto modificado.
        #    Odoo se encargará de renderizar la plantilla base y nuestras herencias.
        html = super().get_html(options, *args, **kwargs)

        if isinstance(html, bytes):
            html = html.decode('utf-8')

        return html

    # get_report_informations NO necesita modificarse para este enfoque
    def get_report_informations(self, options):
        info = super().get_report_informations(options)
        info['show_sign_area'] = self.show_sign_area
        # info['report'] = self # Ya lo pasamos en get_html via additional_context
        return info

    # _get_report_main_template_name ya no es necesario aquí
    # def _get_report_main_template_name(self):
    #      return 'account_reports.main_template'