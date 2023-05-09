# Copyright (c) 2013, Aerele Technologies Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests, json
from erpnext.accounts.report.accounts_receivable.accounts_receivable import execute as execute_account_receivable
from frappe.utils import today, cint, flt, nowdate, add_to_date
from frappe.www.printview import get_print_style
from dateutil.relativedelta import relativedelta
from datetime import datetime
from essdee.essdee.report.party_ledger.party_ledger import image_conversion

def execute(filters=None):
	columns, data = [], []
	if not 'customer' in filters:
		return columns, data 

	columns = data = c = d = e = f = None
	columns, data, c, d, e, f = execute_account_receivable(filters)
	for column in columns:
		if 'fieldtype' in column and (column['fieldtype'] == 'Link' or column['fieldtype'] == 'Dynamic Link'):
			if True or not (column['fieldname'] == 'party' or column['fieldname'] == 'voucher_no'): # remove true to enable link field
				column['fieldtype'] = 'Data'
				del column['options']
	return columns, data, c, d, e, f

def get_outstanding_summary(customer, company):
	avg_days_list = calculate_avg_days({'report_date': today()}, [customer])
	avg_days = avg_days_list[customer] if customer in avg_days_list else None
	gl_entry = frappe.db.sql(
		"""select posting_date, sum(credit), sum(debit)
		from `tabGL Entry` where docstatus=1 and company=%(company)s and
		party_type=%(party_type)s and party=%(party)s and voucher_type=%(voucher_type)s
		group by voucher_no
		order by posting_date desc,voucher_no desc limit %(list_limit)s""",
		{"company": company,
		"party_type": "Customer",
		"party": customer,
		"voucher_type": 'Payment Entry',
		"list_limit": 1},
		as_list=1)
	return {
		"last_payment_date": gl_entry[0][0].strftime('%d-%m-%Y') if gl_entry else None,
		"last_payment_amount": round(abs(gl_entry[0][1]-gl_entry[0][2]), 2) if gl_entry else None,
		"avg_payment_days": avg_days
	}

@frappe.whitelist()
def get_custom_outstanding_list(customer, list_limit):
	list_limit = cint(list_limit)
	default_company = frappe.defaults.get_user_default("Company")
	outstanding_list = []
	summary = {}
	total_outstanding = 0
	total_due = 0
	due_days = frappe.get_single('Essdee Application Settings').due_days
	outstanding_filters = {'company': default_company,
	'report_date': today(),
	'ageing_based_on': 'Posting Date',
	'range1': 30,
	'range2': 60,
	'range3': 90,
	'range4': 120,
	'customer': customer}
	columns, data, c, d, e, f = execute(outstanding_filters)
	if list_limit:
		data = data[:list_limit]
	if data:
		for entry in data:
			if entry['age'] > cint(due_days):
				total_due+= entry['outstanding']
			outstanding_list.append({
				"date": entry['posting_date'].strftime('%d-%m-%Y'),
				"voucher_no": entry['voucher_no'],
				"voucher_type": entry['voucher_type'],
				"outstanding_amount": entry['outstanding'],
				"age": entry['age']
			})
			total_outstanding += entry['outstanding']

		partial_summary = get_outstanding_summary(customer, default_company)
		summary = {
		"total_outstanding": total_outstanding,
		"total_due": total_due,
		"last_payment_date": partial_summary['last_payment_date'],
		"last_payment_amount": partial_summary['last_payment_amount'],
		"avg_payment_days": partial_summary['avg_payment_days']
		}

	return {"summary": summary, 'list': outstanding_list}


@frappe.whitelist()
def get_outstanding_print_html(customer=None, outstanding_filters=None):
	default_company = frappe.defaults.get_user_default("Company")
	if not outstanding_filters:
		outstanding_filters = {'company': default_company,
		'report_date': today(),
		'ageing_based_on': 'Posting Date',
		'range1': 30,
		'range2': 60,
		'range3': 90,
		'range4': 120,
		'customer': customer}
	if isinstance(outstanding_filters, str):
		outstanding_filters = eval(outstanding_filters)
	if 'customer' in outstanding_filters:
		city=frappe.db.get_value("Customer",outstanding_filters['customer'],"city")
		columns, data, c, d, e, f = execute(outstanding_filters)
		letterhead_doc = frappe.get_doc("Letter Head", {"is_default": 1})
		outstanding_filters['letter_head'] = letterhead_doc.content
		outstanding_filters["city"]=city
		base_template_path = "frappe/www/printview.html"
		template_path = "essdee/essdee/report/party_outstanding/party_outstanding.html"
		summary = frappe._dict(get_outstanding_summary(outstanding_filters['customer'], default_company))
		if data:
			html = frappe.render_template(template_path, \
					{"filters": outstanding_filters, "data": data, "summary": summary})
			html = frappe.render_template(base_template_path, {"body": html, \
					"css": get_print_style(), "title": "Statement For " + outstanding_filters['customer']})
			return image_conversion(html)


def calculate_avg_days(outstanding_filters, customers):
	period = outstanding_filters['period'] if 'period' in outstanding_filters else 14
	if 'report_date' in outstanding_filters and outstanding_filters['report_date']:
		outstanding_filters['from_date'] = (datetime.strptime(outstanding_filters['report_date'], '%Y-%m-%d') - relativedelta(months=period)).strftime('%Y-%m-%d')
	return get_avg_days(list(customers), outstanding_filters['from_date'])

def get_avg_days(customer_list=None, from_date=None, to_date=None, company=None):
	if not to_date:
		to_date = nowdate()
	if not from_date:
		from_date = add_to_date(to_date, years=1)
	if not company:
		from erpnext import get_default_company
		company = get_default_company()

	avg_payment_days_list = frappe.db.sql("""SELECT gl.party as customer,
		ROUND(sum((gl.credit - gl.debit) * DATEDIFF(gl.posting_date, inv.posting_date)) / (sum(gl.credit - gl.debit)), 2) avg_payment_days
		from `tabGL Entry` as gl,
			`tabSales Invoice` as inv
		WHERE gl.voucher_type = "Payment Entry"
			AND gl.party_type = "Customer"
			AND gl.docstatus = 1
			AND gl.against_voucher = inv.name
			AND gl.company = %(company)s
			{0}
			AND gl.posting_date >= %(from_date)s
			AND gl.posting_date <= %(to_date)s
		GROUP BY gl.party;""".format(" AND gl.party IN %(customers)s " if customer_list else " "),
		{
		"company":company,
		"customers": customer_list,
		"from_date": from_date,
		"to_date": to_date
		}, as_dict=1)

	avg_payment_days_dict = dict()
	for row in avg_payment_days_list:
		avg_payment_days_dict[row.customer] = row.avg_payment_days
	return avg_payment_days_dict
	
