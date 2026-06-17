from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_open_apply_invoice_template_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Apply Invoice Template',
            'res_model': 'invoice.template.apply.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_id': self.id,
                'default_company_id': self.company_id.id,
            },
        }

    def _get_al_fouad_previous_balance(self):
        self.ensure_one()
        partner = self.commercial_partner_id or self.partner_id
        if not partner:
            return 0.0

        balance_date = self.invoice_date or self.date
        domain = [
            ('parent_state', '=', 'posted'),
            ('company_id', '=', self.company_id.id),
            ('partner_id', 'child_of', partner.id),
            ('account_id.account_type', 'in', ('asset_receivable', 'liability_payable')),
            ('move_id', '!=', self.id),
        ]
        if balance_date:
            domain += [
                '|',
                ('date', '<', balance_date),
                '&',
                ('date', '=', balance_date),
                ('move_id', '<', self.id),
            ]

        result = self.env['account.move.line'].sudo().read_group(domain, ['balance:sum'], [])
        return result[0].get('balance', 0.0) if result else 0.0

    def _get_al_fouad_after_balance(self):
        self.ensure_one()
        previous_balance = self._get_al_fouad_previous_balance()
        return previous_balance + self.amount_residual_signed

    def _get_al_fouad_paid_amount(self):
        self.ensure_one()
        return self.amount_total - self.amount_residual
