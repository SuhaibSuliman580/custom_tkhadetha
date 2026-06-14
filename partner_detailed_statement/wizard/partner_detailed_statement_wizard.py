# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountReportPartnerDetailedStatement(models.TransientModel):
    _name = 'account.report.partner.detailed.statement'
    _inherit = 'account.common.partner.report'
    _description = 'Detailed Partner Statement'

    include_invoice_lines = fields.Boolean(string='Show Invoice Lines', default=True)
    include_payments = fields.Boolean(string='Show Linked Payments', default=True)

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
