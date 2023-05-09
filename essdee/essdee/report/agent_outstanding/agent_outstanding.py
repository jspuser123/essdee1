# Copyright (c) 2013, Aerele Technologies Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.www.printview import get_print_style
from frappe.utils import today, now_datetime, cint
from erpnext.accounts.report.accounts_receivable.accounts_receivable import execute as execute_account_receivable
import json
from frappe.desk.query_report import get_prepared_report_result, get_report_doc, background_enqueue_run
from essdee.essdee.doctype.essdee_application_settings.essdee_application_settings import time_diff_in_minutes

def execute(filters=None):
	columns, data = [], []
	if not 'customer_group' in filters:
		customer_group = frappe.get_value('User Permission',{'user':frappe.session.user,'allow':'Customer Group'},'for_value')
		if not customer_group:
			return columns, data 
		filters['customer_group'] = customer_group 
	columns, data = get_customer_details(data, filters)
	if not columns:
		return columns, data
	for column in columns:
		if 'fieldtype' in column and (column['fieldtype'] == 'Link' or column['fieldtype'] == 'Dynamic Link'):
			if not (column['fieldname'] == 'party' or column['fieldname'] == 'voucher_no'):
				column['fieldtype'] = 'Data'
				del column['options']
	return columns, data

def get_customer_details(data, filters):
	detail = None
	customer_list = sorted([customer['name'] for customer in frappe.get_list('Customer',{'customer_group':filters['customer_group']})])
	final_total = 0
	if customer_list:
		for customer in customer_list:
			filters['customer'] = customer
			columns, detail, c, d, e, f = execute_account_receivable(filters)
			if detail:
				total_out_amt = 0
				city = ''
				mobile_no = ''
				addresses = frappe.get_list("Dynamic Link",{"parentfield": "links","parenttype": "Address","link_doctype": "Customer","link_name": customer},"parent")
				contacts = frappe.get_list("Dynamic Link",{"parentfield": "links","parenttype": "Contact","link_doctype": "Customer","link_name": customer},"parent")
				if addresses:
					city = frappe.get_value('Address', addresses[-1]['parent'],'city')
				if contacts:
					mobile_no = frappe.get_value('Contact', contacts[-1]['parent'],'mobile_no')
				for d in detail:
					d['outstanding'] = cint(d['outstanding'])
					d['invoiced'] = cint(d['invoiced'])
					d['paid'] = cint(d['paid'])
					d['credit_note'] = cint(d['credit_note'])
					d['age'] = cint(d['age'])
					total_out_amt += d['outstanding']
				final_total += total_out_amt
				data.append({'posting_date':'',
						'party':customer,
						'customer_primary_contact':f'{city} \n Ph:{mobile_no}', 
						'voucher_no': '',
						'outstanding': cint(total_out_amt),
						'invoiced': '',
						'paid': '',
						'credit_note': '',
						'age': None
						})
				data.extend(detail)
		if final_total:
			data.append({'posting_date':'',
						'party':'Total',
						'customer_primary_contact':'', 
						'voucher_no': '',
						'invoiced': '',
						'paid': '',
						'outstanding': cint(final_total),
						'credit_note': '',
						'age': None})
		return columns, data
	return []

@frappe.whitelist()
def get_agent_outstanding_print_html(customer_group=None, outstanding_filters=None, prepared_report_name=''):

	user = frappe.session.user
	if not outstanding_filters:
		default_company = frappe.defaults.get_user_default("Company")
		outstanding_filters = {'company': default_company,
		'report_date': today(),
		'ageing_based_on': 'Posting Date',
		'range1': 30,
		'range2': 60,
		'range3': 90,
		'range4': 120,
		'customer_group': customer_group}
	if isinstance(outstanding_filters, str):
		outstanding_filters = eval(outstanding_filters)

	if 'customer_group' in outstanding_filters:
		report = get_report_doc('Agent Outstanding')
		data = get_prepared_report_result(report, outstanding_filters, prepared_report_name, user)
		prepared_report_doc = data['doc']

		base_template_path = "frappe/www/printview.html"
		template_path = "essdee/essdee/report/agent_outstanding/agent_outstanding.html"
		if 'result' in data:
			data = data['result']
			html = frappe.render_template(template_path, \
					{"filters": outstanding_filters, "data": data, "doc": prepared_report_doc})
			html = frappe.render_template(base_template_path, {"body": html, \
					"css": get_print_style(), "title": "Statement For " + outstanding_filters['customer_group']})
			
			return html