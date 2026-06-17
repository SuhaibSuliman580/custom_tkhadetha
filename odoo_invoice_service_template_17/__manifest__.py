{
    'name': 'Invoice Service Templates',
    'version': '17.0.1.1.0',
    'summary': 'Apply predefined service templates directly on customer invoices for Odoo 17',
    'description': '''
Create reusable invoice templates and apply them directly on customer invoices.
Each template inserts normal invoice lines, so every service keeps its own
income account, taxes, analytic distribution, and journal behavior.
    ''',
    'category': 'Accounting',
    'author': 'OpenAI',
    'license': 'LGPL-3',
    'depends': ['branch', 'account', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/invoice_service_template_views.xml',
        'wizard/invoice_template_apply_wizard_views.xml',
        'views/account_move_views.xml',
        'report/customer_invoice_report.xml',
    ],
    'installable': True,
    'application': False,
}
