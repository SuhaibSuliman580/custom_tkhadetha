# -*- coding: utf-8 -*-

import base64
import io

from odoo import fields, models
from odoo.tools.misc import get_lang

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class AccountReportPartnerDetailedStatement(models.TransientModel):
    _name = 'account.report.partner.detailed.statement'
    _inherit = 'account.common.partner.report'
    _description = 'Detailed Partner Statement'

    include_invoice_lines = fields.Boolean(string='Show Invoice Lines', default=True)
    include_payments = fields.Boolean(string='Show Linked Payments', default=True)

    def _prepare_statement_data(self):
        self.ensure_one()
        data = {
            'ids': self.env.context.get('active_ids', []),
            'model': self.env.context.get('active_model', 'ir.ui.menu'),
            'form': self.read(['date_from', 'date_to', 'journal_ids', 'target_move', 'company_id'])[0],
        }
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=get_lang(self.env).code)
        return self._get_report_data(data)

    def _get_report_data(self, data):
        data = self.pre_print_report(data)
        data['form'].update({
            'include_invoice_lines': self.include_invoice_lines,
            'include_payments': self.include_payments,
        })
        return data

    def _print_report(self, data):
        data = self._get_report_data(data)
        return self.env.ref(
            'partner_detailed_statement.action_report_partner_detailed_statement'
        ).with_context(landscape=True).report_action(self, data=data)

    def action_xlsx(self):
        self.ensure_one()
        data = self._prepare_statement_data()
        report = self.env['report.partner_detailed_statement.statement']
        labels = report._labels()
        is_arabic = report._is_arabic()
        partners = report._get_partners(data)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(labels['title'][:31])
        if is_arabic:
            sheet.right_to_left()
        sheet.set_landscape()
        sheet.fit_to_pages(1, 0)

        title_format = workbook.add_format({
            'bold': True, 'font_size': 18, 'font_color': 'white',
            'bg_color': '#0F4C5C', 'align': 'center', 'valign': 'vcenter',
            'border': 1
        })
        meta_label = workbook.add_format({
            'bold': True, 'font_color': '#0F4C5C', 'bg_color': '#F6FAFB',
            'border': 1, 'align': 'right' if is_arabic else 'left',
            'valign': 'vcenter'
        })
        meta_value = workbook.add_format({
            'bg_color': '#F6FAFB', 'border': 1,
            'align': 'right' if is_arabic else 'left', 'valign': 'vcenter'
        })
        partner_format = workbook.add_format({
            'bold': True, 'font_size': 13, 'font_color': '#0F4C5C',
            'bg_color': '#EAF4F6', 'border': 1,
            'align': 'right' if is_arabic else 'left', 'valign': 'vcenter'
        })
        header_format = workbook.add_format({
            'bold': True, 'font_color': '#17324D', 'bg_color': '#DBEAFE',
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'top': 2, 'bottom': 1
        })
        line_header_format = workbook.add_format({
            'bold': True, 'font_color': '#14532D', 'bg_color': '#ECFDF5',
            'border': 1, 'align': 'center', 'valign': 'vcenter'
        })
        text_format = workbook.add_format({
            'border': 1, 'align': 'right' if is_arabic else 'left',
            'valign': 'vcenter', 'text_wrap': True
        })
        date_format = workbook.add_format({'border': 1, 'align': 'center', 'num_format': 'yyyy-mm-dd'})
        currency_symbol = self.env.company.currency_id.symbol or ''
        money_format = workbook.add_format({
            'border': 1, 'align': 'right',
            'num_format': '#,##0.00%s' % (' "%s"' % currency_symbol if currency_symbol else '')
        })
        subtotal_format = workbook.add_format({
            'border': 1, 'align': 'right',
            'num_format': '#,##0.00%s' % (' "%s"' % currency_symbol if currency_symbol else ''),
            'bg_color': '#F0F9FF'
        })
        empty_format = workbook.add_format({'italic': True, 'font_color': '#6B7280', 'border': 1})

        sheet.set_column('A:A', 34)
        sheet.set_column('B:B', 13)
        sheet.set_column('C:C', 15)
        sheet.set_column('D:D', 28)
        sheet.set_column('E:G', 15)
        sheet.set_column('H:H', 14)

        row = 0
        sheet.merge_range(row, 0, row + 1, 7, labels['title'], title_format)
        sheet.set_row(row, 28)
        row += 3

        company = data['form']['company_id'][1] if data['form'].get('company_id') else self.env.company.name
        partner_filter = {
            'customer': labels['customers'],
            'supplier': labels['vendors'],
            'customer_supplier': labels['customers_vendors'],
        }.get(data['form'].get('result_selection'), '')
        target_move = labels['posted_entries'] if data['form'].get('target_move') == 'posted' else labels['all_entries']

        meta_items = [
            (labels['company'], company),
            (labels['date_from'], data['form'].get('date_from') or ''),
            (labels['date_to'], data['form'].get('date_to') or ''),
            (labels['partners'], partner_filter),
            (labels['target_moves'], target_move),
        ]
        col = 0
        for label, value in meta_items:
            sheet.write(row, col, label, meta_label)
            sheet.write(row + 1, col, value, meta_value)
            col += 1
        row += 4

        for partner in partners:
            statement = report._partner_statement(data, partner)
            partner_name = '%s%s%s' % (partner.ref or '', ' - ' if partner.ref else '', partner.name or '')
            sheet.merge_range(row, 0, row, 7, partner_name, partner_format)
            sheet.set_row(row, 22)
            row += 1

            sheet.write(row, 0, labels['opening_balance'], meta_label)
            sheet.write_number(row, 1, statement['opening_balance'], subtotal_format)
            sheet.write(row, 2, labels['ending_balance'], meta_label)
            sheet.write_number(row, 3, statement['ending_balance'], subtotal_format)
            row += 2

            headers = [
                labels['movement'], labels['date'], labels['journal'], labels['account'],
                labels['debit'], labels['credit'], labels['balance_after']
            ]
            for index, header in enumerate(headers):
                sheet.write(row, index, header, header_format)
            row += 1

            if not statement['rows']:
                sheet.merge_range(row, 0, row, 6, labels['no_movements'], empty_format)
                row += 2
                continue

            for item in statement['rows']:
                line = item['line']
                sheet.write(row, 0, item['label'], text_format)
                sheet.write(row, 1, item['date'].strftime('%Y-%m-%d') if item['date'] else '', date_format)
                sheet.write(row, 2, line.journal_id.code or '', text_format)
                sheet.write(row, 3, line.account_id.display_name or '', text_format)
                sheet.write_number(row, 4, item['debit'], money_format)
                sheet.write_number(row, 5, item['credit'], money_format)
                sheet.write_number(row, 6, item['invoice_balance'], money_format)
                row += 1

                invoice = item['invoice']
                if invoice and data['form'].get('include_invoice_lines'):
                    line_headers = [
                        labels['product_service'], labels['quantity'], labels['unit'],
                        labels['unit_price'], labels['discount'], labels['subtotal']
                    ]
                    for index, header in enumerate(line_headers):
                        sheet.write(row, index, header, line_header_format)
                    row += 1

                    if not item['lines']:
                        sheet.merge_range(row, 0, row, 5, labels['no_invoice_lines'], empty_format)
                        row += 1
                    for invoice_line in item['lines']:
                        sheet.write(row, 0, invoice_line['name'], text_format)
                        sheet.write_number(row, 1, invoice_line['quantity'], money_format)
                        sheet.write(row, 2, invoice_line['uom'], text_format)
                        sheet.write_number(row, 3, invoice_line['price_unit'], money_format)
                        sheet.write_number(row, 4, invoice_line['discount'], money_format)
                        sheet.write_number(row, 5, invoice_line['subtotal'], money_format)
                        row += 1
            row += 2

        workbook.close()
        output.seek(0)
        filename = 'Detailed_Partner_Statement.xlsx'
        attachment = self.env['ir.attachment'].sudo().create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }
