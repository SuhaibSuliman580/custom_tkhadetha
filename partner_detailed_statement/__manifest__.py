# -*- coding: utf-8 -*-

{
    'name': 'Detailed Partner Statement',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Detailed customer and vendor statement with invoices, lines, payments, and running balance',
    'description': """
Detailed customer and vendor statement.

The report shows invoice number, invoice date, invoice lines, total,
linked payments, and running balance, with filters by date and partner.
    """,
    'author': 'Custom Markaz',
    'license': 'LGPL-3',
    'depends': ['accounting_pdf_reports'],
    'data': [
        'security/ir.model.access.csv',
        'data/cleanup.xml',
        'wizard/partner_detailed_statement_wizard.xml',
        'report/partner_detailed_statement_report.xml',
        'report/report.xml',
    ],
    'installable': True,
    'application': False,
}
