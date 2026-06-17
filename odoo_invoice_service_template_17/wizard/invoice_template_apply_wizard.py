from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class InvoiceTemplateApplyWizard(models.TransientModel):
    _name = 'invoice.template.apply.wizard'
    _description = 'Apply Invoice Template Wizard'

    move_id = fields.Many2one('account.move', required=True)
    company_id = fields.Many2one('res.company', required=True, readonly=True)
    branch_id = fields.Many2one('res.branch', readonly=True)
    template_id = fields.Many2one(
        'invoice.service.template',
        required=True,
        domain="[('company_id', '=', company_id), ('active', '=', True), '|', ('branch_id', '=', False), ('branch_id', '=', branch_id)]",
    )
    replace_existing = fields.Boolean(
        string='Replace Existing Lines',
        help='If enabled, current invoice product lines will be removed before loading the template.',
    )

    @api.constrains('move_id')
    def _check_move_id(self):
        for rec in self:
            if rec.move_id.move_type != 'out_invoice':
                raise ValidationError(_('This wizard only works for customer invoices.'))
            if rec.move_id.state != 'draft':
                raise ValidationError(_('Only draft invoices are supported.'))
            if rec.template_id and rec.template_id.branch_id and rec.move_id.branch_id and rec.template_id.branch_id != rec.move_id.branch_id:
                raise ValidationError(_('The selected template belongs to another branch.'))

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        move_id = res.get('move_id') or self.env.context.get('default_move_id')
        if move_id:
            move = self.env['account.move'].browse(move_id)
            if move.exists():
                res.setdefault('branch_id', move.branch_id.id)
        return res

    def action_apply(self):
        self.ensure_one()
        self.template_id.action_apply_to_invoice(self.move_id, replace_existing=self.replace_existing)
        return {'type': 'ir.actions.act_window_close'}

