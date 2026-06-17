from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class InvoiceServiceTemplate(models.Model):
    _name = 'invoice.service.template'
    _description = 'Invoice Service Template'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.user.branch_id, index=True)
    line_ids = fields.One2many(
        'invoice.service.template.line',
        'template_id',
        string='Template Lines',
        copy=True,
    )
    note = fields.Text()

    _sql_constraints = [
        ('name_company_unique', 'unique(name, company_id)', 'Template name must be unique per company.'),
    ]

    def action_apply_to_invoice(self, move, replace_existing=False):
        self.ensure_one()
        if self.branch_id and move.branch_id and self.branch_id != move.branch_id:
            raise ValidationError(_('Template branch must match invoice branch.'))
        if move.move_type != 'out_invoice':
            raise ValidationError(_('This template can only be applied to customer invoices.'))
        if move.state != 'draft':
            raise ValidationError(_('You can only apply templates on draft invoices.'))

        if replace_existing:
            product_lines = move.invoice_line_ids.filtered(lambda l: not l.display_type)
            product_lines.unlink()

        new_lines = []
        sequence = (max(move.invoice_line_ids.mapped('sequence')) + 1) if move.invoice_line_ids else 10
        for line in self.line_ids.sorted(key=lambda l: (l.sequence, l.id)):
            vals = line._prepare_invoice_line_vals(move)
            vals['sequence'] = sequence
            sequence += 1
            new_lines.append((0, 0, vals))

        if new_lines:
            move.write({'invoice_line_ids': new_lines})

        return True


class InvoiceServiceTemplateLine(models.Model):
    _name = 'invoice.service.template.line'
    _description = 'Invoice Service Template Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    template_id = fields.Many2one(
        'invoice.service.template',
        required=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(related='template_id.company_id', store=True, readonly=True)
    branch_id = fields.Many2one(related='template_id.branch_id', store=True, readonly=True)
    product_id = fields.Many2one(
        'product.product',
        required=True,
        domain="[('sale_ok', '=', True)]",
    )
    name = fields.Char('Description')
    quantity = fields.Float(default=1.0, digits='Product Unit of Measure')
    price_unit = fields.Float('Unit Price', digits='Product Price')
    tax_ids = fields.Many2many('account.tax', string='Taxes')
    analytic_distribution = fields.Json(string='Analytic Distribution')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for rec in self:
            if not rec.product_id:
                continue
            product = rec.product_id
            rec.name = product.get_product_multiline_description_sale() or product.display_name
            rec.price_unit = product.lst_price
            taxes = product.taxes_id.filtered(lambda t: not rec.company_id or t.company_id == rec.company_id)
            rec.tax_ids = taxes

    @api.constrains('product_id')
    def _check_product_company(self):
        for rec in self:
            company = rec.company_id
            product_company = rec.product_id.company_id
            if company and product_company and product_company != company:
                raise ValidationError(_('The product company must match the template company.'))

    def _prepare_invoice_line_vals(self, move):
        self.ensure_one()
        product = self.product_id
        description = self.name or product.get_product_multiline_description_sale() or product.display_name
        taxes = self.tax_ids
        if not taxes:
            taxes = product.taxes_id.filtered(lambda t: t.company_id == move.company_id)

        return {
            'move_id': move.id,
            'product_id': product.id,
            'name': description,
            'quantity': self.quantity,
            'price_unit': self.price_unit if self.price_unit or self.price_unit == 0 else product.lst_price,
            'tax_ids': [(6, 0, taxes.ids)],
            'analytic_distribution': self.analytic_distribution or False,
        }
