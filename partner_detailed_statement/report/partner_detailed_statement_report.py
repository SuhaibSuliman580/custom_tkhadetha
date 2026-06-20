# -*- coding: utf-8 -*-

import time

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ReportPartnerDetailedStatement(models.AbstractModel):
    _name = 'report.partner_detailed_statement.statement'
    _description = 'Detailed Partner Statement Report'

    def _get_account_types(self, result_selection):
        if result_selection == 'supplier':
            return ['liability_payable']
        if result_selection == 'customer':
            return ['asset_receivable']
        return ['asset_receivable', 'liability_payable']

    def _get_invoice_types(self, result_selection):
        if result_selection == 'supplier':
            return ['in_invoice', 'in_refund']
        if result_selection == 'customer':
            return ['out_invoice', 'out_refund']
        return ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']

    def _is_arabic(self):
        return (self.env.context.get('lang') or '').startswith('ar')

    def _labels(self):
        labels = {
            'title': 'Detailed Partner Statement',
            'company': 'Company:',
            'date_from': 'Date from:',
            'date_to': 'Date to:',
            'partners': 'Partners:',
            'customers': 'Customers',
            'vendors': 'Vendors',
            'customers_vendors': 'Customers and Vendors',
            'target_moves': 'Target Moves:',
            'all_entries': 'All Entries',
            'posted_entries': 'Posted Entries',
            'opening_balance': 'Opening Balance',
            'ending_balance': 'Ending Balance',
            'no_movements': 'No invoice or payment movements found for the selected filters.',
            'movement': 'Movement',
            'invoice_no': 'Invoice No.',
            'date': 'Date',
            'description': 'Description',
            'journal': 'Journal',
            'account': 'Account',
            'debit': 'Debit',
            'credit': 'Credit',
            'balance_after': 'Balance After',
            'invoice_total': 'Invoice Total',
            'residual': 'Residual',
            'payment_status': 'Payment Status',
            'product_service': 'Product / Service',
            'notes': 'Notes',
            'quantity': 'Quantity',
            'unit': 'Unit',
            'unit_price': 'Unit Price',
            'discount': 'Discount %',
            'subtotal': 'Subtotal',
            'no_invoice_lines': 'No invoice lines found.',
            'payment_settlement': 'Payment / Settlement',
            'reference': 'Reference',
            'amount': 'Amount',
            'line_value': 'Value',
        }
        if not self._is_arabic():
            return labels
        labels.update({
            'title': 'كشف تفصيلي للعملاء والموردين',
            'company': 'الشركة:',
            'date_from': 'من تاريخ:',
            'date_to': 'إلى تاريخ:',
            'partners': 'الشركاء:',
            'customers': 'العملاء',
            'vendors': 'الموردون',
            'customers_vendors': 'العملاء والموردون',
            'target_moves': 'حالة القيود:',
            'all_entries': 'كل القيود',
            'posted_entries': 'القيود المرحلة',
            'opening_balance': 'الرصيد الافتتاحي',
            'ending_balance': 'الرصيد الختامي',
            'no_movements': 'لا توجد حركات فواتير أو دفعات حسب عوامل التصفية المحددة.',
            'movement': 'الحركة',
            'invoice_no': 'رقم الفاتورة',
            'date': 'التاريخ',
            'description': 'الوصف',
            'journal': 'اليومية',
            'account': 'الحساب',
            'debit': 'مدين',
            'credit': 'دائن',
            'balance_after': 'الرصيد بعد الحركة',
            'invoice_total': 'إجمالي الفاتورة',
            'residual': 'المتبقي',
            'payment_status': 'حالة السداد',
            'product_service': 'المنتج / الخدمة',
            'quantity': 'الكمية',
            'unit': 'الوحدة',
            'unit_price': 'سعر الوحدة',
            'discount': 'نسبة الخصم',
            'subtotal': 'الإجمالي الفرعي',
            'no_invoice_lines': 'لا توجد بنود للفاتورة.',
            'payment_settlement': 'دفعة / تسوية',
            'reference': 'المرجع',
            'amount': 'المبلغ',
            'line_value': 'القيمة',
        })
        labels['notes'] = 'ملاحظات'
        return labels

    def _base_invoice_domain(self, data):
        form = data['form']
        domain = [
            ('company_id', '=', form['company_id'][0]),
            ('move_type', 'in', self._get_invoice_types(form.get('result_selection'))),
        ]
        if form.get('target_move') == 'posted':
            domain.append(('state', '=', 'posted'))
        else:
            domain.append(('state', 'in', ['draft', 'posted']))
        if form.get('journal_ids'):
            domain.append(('journal_id', 'in', form['journal_ids']))
        if form.get('date_to'):
            domain.append(('invoice_date', '<=', form['date_to']))
        return domain

    def _base_line_domain(self, data, account_types):
        form = data['form']
        domain = [
            ('company_id', '=', form['company_id'][0]),
            ('account_id.account_type', 'in', account_types),
            ('display_type', 'not in', ('line_section', 'line_note')),
        ]
        if form.get('target_move') == 'posted':
            domain.append(('parent_state', '=', 'posted'))
        else:
            domain.append(('parent_state', 'in', ['draft', 'posted']))
        if form.get('journal_ids'):
            domain.append(('journal_id', 'in', form['journal_ids']))
        if form.get('date_from'):
            domain.append(('date', '>=', form['date_from']))
        if form.get('date_to'):
            domain.append(('date', '<=', form['date_to']))
        return domain

    def _to_date(self, value):
        if not value or hasattr(value, 'year'):
            return value
        return fields.Date.from_string(value)

    def _invoice_in_period(self, invoice, data):
        date_from = self._to_date(data['form'].get('date_from'))
        date_to = self._to_date(data['form'].get('date_to'))
        invoice_date = invoice.invoice_date or invoice.date
        if date_from and invoice_date and invoice_date < date_from:
            return False
        if date_to and invoice_date and invoice_date > date_to:
            return False
        return True

    def _payment_in_period(self, payment, data):
        date_from = self._to_date(data['form'].get('date_from'))
        date_to = self._to_date(data['form'].get('date_to'))
        payment_date = payment['date']
        if date_from and payment_date and payment_date < date_from:
            return False
        if date_to and payment_date and payment_date > date_to:
            return False
        return True

    def _partner_account_lines(self, move, account_types):
        return move.line_ids.filtered(
            lambda line: line.account_id.account_type in account_types
            and line.display_type not in ('line_section', 'line_note')
        )

    def _invoice_delta(self, invoice, account_types):
        return sum(self._partner_account_lines(invoice, account_types).mapped('balance'))

    def _invoice_line_values(self, invoice):
        lines = []
        invoice_lines = invoice.invoice_line_ids.sorted(
            key=lambda item: (item.sequence, item.id)
        )
        if not invoice_lines.filtered(
            lambda item: item.display_type not in ('line_section', 'line_note')
        ):
            invoice_lines = invoice.line_ids.filtered(
                lambda item: item.display_type not in ('line_section', 'line_note')
                and item.account_id.account_type not in ('asset_receivable', 'liability_payable')
                and not item.tax_line_id
            )
        for line in invoice_lines:
            if line.display_type == 'line_section':
                continue
            if line.display_type == 'line_note':
                if lines and line.name:
                    current_notes = lines[-1]['notes']
                    lines[-1]['notes'] = '\n'.join(
                        value for value in (current_notes, line.name) if value
                    )
                continue
            subtotal = line.price_subtotal if 'price_subtotal' in line._fields else abs(line.balance)
            if not subtotal and line.balance:
                subtotal = abs(line.balance)
            lines.append({
                'name': line.product_id.display_name or line.name,
                'notes': line.statement_note or '' if 'statement_note' in line._fields else '',
                'quantity': line.quantity if 'quantity' in line._fields else 1.0,
                'uom': line.product_uom_id.name if 'product_uom_id' in line._fields else '',
                'price_unit': line.price_unit if 'price_unit' in line._fields else subtotal,
                'discount': line.discount if 'discount' in line._fields else 0.0,
                'subtotal': subtotal,
            })
        return lines

    def _displayed_line_name(self, line):
        values = (line.move_id.name, line.ref, line.name)
        return ' - '.join(str(value) for value in values if value not in (None, False, '', '/')) or '/'

    def _payment_values(self, invoice, account_types):
        payments = []
        seen = set()
        for line in self._partner_account_lines(invoice, account_types):
            for partial in line.matched_credit_ids:
                counterpart = partial.credit_move_id
                if partial.id in seen:
                    continue
                seen.add(partial.id)
                payments.append(self._prepare_payment_value(partial, counterpart, -partial.amount))
            for partial in line.matched_debit_ids:
                counterpart = partial.debit_move_id
                if partial.id in seen:
                    continue
                seen.add(partial.id)
                payments.append(self._prepare_payment_value(partial, counterpart, partial.amount))
        return sorted(payments, key=lambda item: (item['date'], item['name']))

    def _prepare_payment_value(self, partial, counterpart, delta):
        move = counterpart.move_id
        payment = counterpart.payment_id if 'payment_id' in counterpart._fields else False
        label = (payment.name if payment else False) or move.name or counterpart.name or '/'
        if move.is_invoice(include_receipts=True):
            label = '%s - %s' % (_('Credit / Bill Adjustment'), move.name or '/')
        return {
            'date': partial.max_date or counterpart.date,
            'name': label,
            'journal': counterpart.journal_id.code or '',
            'amount': partial.amount,
            'delta': delta,
            'ref': move.ref or counterpart.ref or '',
        }

    def _opening_balance(self, partner, data, account_types):
        date_from = data['form'].get('date_from')
        if not date_from:
            return 0.0

        domain = [
            ('company_id', '=', data['form']['company_id'][0]),
            ('partner_id', 'child_of', partner.id),
            ('account_id.account_type', 'in', account_types),
            ('date', '<', date_from),
        ]
        if data['form'].get('target_move') == 'posted':
            domain.append(('parent_state', '=', 'posted'))
        else:
            domain.append(('parent_state', 'in', ['draft', 'posted']))
        if data['form'].get('journal_ids'):
            domain.append(('journal_id', 'in', data['form']['journal_ids']))

        result = self.env['account.move.line'].read_group(domain, ['balance:sum'], [])
        return result[0]['balance'] if result else 0.0

    def _partner_statement(self, data, partner):
        account_types = self._get_account_types(data['form'].get('result_selection'))
        domain = self._base_line_domain(data, account_types)
        domain.append(('partner_id', 'child_of', partner.commercial_partner_id.id))
        move_lines = self.env['account.move.line'].search(domain, order='date, id')

        rows = []
        running_balance = self._opening_balance(partner.commercial_partner_id, data, account_types)
        opening_balance = running_balance

        for line in move_lines:
            move = line.move_id
            invoice = move if move.is_invoice(include_receipts=True) else False
            running_balance += line.balance
            invoice_balance = running_balance

            rows.append({
                'line': line,
                'invoice': invoice,
                'date': line.date,
                'label': self._displayed_line_name(line),
                'debit': line.debit,
                'credit': line.credit,
                'lines': self._invoice_line_values(invoice) if invoice else [],
                'invoice_delta': line.balance,
                'invoice_balance': invoice_balance,
                'payments': [],
                'ending_balance': running_balance,
            })

        return {
            'opening_balance': opening_balance,
            'ending_balance': running_balance,
            'rows': rows,
        }

    def _get_partners(self, data):
        partner_model = self.env['res.partner']
        account_types = self._get_account_types(data['form'].get('result_selection'))
        selected_ids = data['form'].get('partner_ids')
        if selected_ids:
            return partner_model.browse(selected_ids).mapped('commercial_partner_id')

        domain = self._base_line_domain(data, account_types)
        domain.append(('partner_id', '!=', False))
        lines = self.env['account.move.line'].search(domain)
        partners = lines.mapped('partner_id.commercial_partner_id')
        return partners.sorted(key=lambda item: (item.ref or '', item.name or ''))

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data or not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        partners = self._get_partners(data)
        statements = {
            partner.id: self._partner_statement(data, partner)
            for partner in partners
        }

        return {
            'doc_ids': partners.ids,
            'doc_model': 'res.partner',
            'data': data,
            'docs': partners,
            'statements': statements,
            'is_arabic': self._is_arabic(),
            'labels': self._labels(),
            'time': time,
        }
