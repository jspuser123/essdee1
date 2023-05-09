# Copyright (c) 2013, Aerele Technologies Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import requests, json
from frappe.utils import today, cint, get_site_path
from frappe.www.printview import get_print_style
import base64
from bs4 import BeautifulSoup

def execute(filters=None):
	columns, data = [], []
	if not 'customer' in filters:
		return columns, data
	else:
		filters['party'] = [filters['customer']]
		filters.pop('customer')
	return get_gl_entries_via_api(filters)

def get_gl_entries_via_api(filters):
	host = '127.0.0.1'
	site_name = frappe.local.site
	port = frappe.get_site_config().webserver_port
	api_key = frappe.db.get_value("User", "Administrator", "api_key")
	api_secret = frappe.utils.password.get_decrypted_password("User", "Administrator", fieldname="api_secret")
	headers = {
		'Accept': 'application/json',
		'Authorization': f'token {api_key}:{api_secret}',
		'Content-Type': 'application/json',
		'X-Forwarded-For':'127.0.0.1',
		'X-Forwarded-Proto': 'https://',
		'X-Frappe-Site-Name': site_name,
		'Host': site_name
	}
	url = f'http://{host}:{port}/api/method/essdee.essdee.report.party_ledger.party_ledger.get_gl_entries'
	payload = {
		'filters': filters
	}
	response = json.loads(requests.request("POST", url, headers=headers, data = json.dumps(payload)).text.encode('utf8'))['message']
	if len(response) == 2:
		columns, data  = response[0], response[1]
	for column in columns:
		if 'fieldtype' in column:
			if column['fieldtype'] == 'Link' or column['fieldtype'] == 'Dynamic Link':
				column['fieldtype'] = 'Data'
				del column['options']
	return columns, data

@frappe.whitelist()
def get_gl_entries(filters):
	columns, data = [], []
	from erpnext.accounts.report.general_ledger.general_ledger import execute as execute_general_ledger
	columns, data = execute_general_ledger(frappe._dict(filters))
	return columns, data

@frappe.whitelist()
def get_custom_ledger_list(customer, list_limit):
	list_limit = cint(list_limit)
	default_company = frappe.defaults.get_user_default("Company")
	abbr = frappe.db.get_value("Company", default_company, "abbr")
	ledger_filters = {
		'company': default_company,
		'from_date': today(),
		'to_date': today(),
		'party_type': 'Customer',
		'group_by': 'Group by Voucher (Consolidated)',
		'presentation_currency': 'INR',
		'party': [customer]}
	col, data = get_gl_entries(ledger_filters)
	running_bal = data[-1].balance
	ledger_list = []
	common_query = """select posting_date,voucher_no,voucher_type,sum(credit),sum(debit),against
		from `tabGL Entry`where docstatus=1 and company=%(company)s and 
		party_type=%(party_type)s and party=%(party)s 
		group by voucher_no 
		order by posting_date desc,voucher_no desc """
	common_query_values = {"company": default_company, "party_type": "Customer", "party": customer}
	if list_limit:
		common_query += 'limit %(list_limit)s'
		common_query_values.update(list_limit=list_limit)
	gl_entry = frappe.db.sql(common_query, common_query_values, as_list=1)

	if gl_entry:
		for entry in gl_entry:
			ledger_list.append({
				"date": entry[0].strftime('%d-%m-%Y'),
				"voucher_no": entry[1],
				"voucher_type": entry[2],
				"amount": round(abs(entry[3]-entry[4]),2),
				"against_account": entry[5].replace(f' - {abbr}', ''),
				"balance": running_bal
			})
			running_bal = (running_bal + entry[3]) if entry[3] else (running_bal - entry[4])
	return {'list': ledger_list}

@frappe.whitelist()
def get_custom_invoice_list(customer, list_limit):
	list_limit = cint(list_limit)
	custom_invoice_list = []
	common_dict = dict(fields={'posting_date',
				'name',
				'grand_total',
				'packing_slip_number',
				'lr_number',
				'lr_date',
				'transport',
				'order_number',
				'number_of_cartons',
				'destination'},
				filters={"customer":customer, "docstatus": 1}, order_by='posting_date desc, name desc')
	if list_limit:
		common_dict.update(limit = list_limit)
	invoice_list = frappe.get_list('Sales Invoice', **common_dict)
	if invoice_list:
		for entry in invoice_list:
			custom_invoice_list.append({
				"date": entry['posting_date'].strftime('%d-%m-%Y'),
				"voucher_no": entry['name'],
				"amount": entry['grand_total'],
				"cashback_claim_status": "NA",
				"packing_slip_no": entry['packing_slip_number'],
				"lr_no": entry['lr_number'],
				"lr_date": entry['lr_date'].strftime('%d-%m-%Y') if entry['lr_date'] else None,
				"transport": entry['transport'],
				"order_no": entry['order_number'],
				"no_of_cartons": entry['number_of_cartons'],
				"destination": entry['destination']
			})
	return {'list': custom_invoice_list}

@frappe.whitelist()
def get_accounts_document_print_html(customer, doctype, doc_name, print_format=None, no_letterhead=0):
	if doctype == "Sales Invoice" and frappe.db.get_value(doctype, doc_name, "customer") != customer:
		current_user = frappe.get_user().name
		frappe.log_error("docname: "+doc_name+"doctype: "+doctype+" | user: "+current_user, "View Invoice PDF Error")
		frappe.throw('Unauthorized customer to view corresponding pdf')

	if print_format is None:
		print_format = frappe.get_meta(doctype).default_print_format
	html=frappe.get_print(doctype, doc_name, print_format, no_letterhead=no_letterhead)
	return image_conversion(html)

@frappe.whitelist()
def get_ledger_print_html(customer=None, from_date=None, to_date=None, ledger_filters=None):
	if not ledger_filters:
		default_company = frappe.defaults.get_user_default("Company")
		ledger_filters = {
			'company': default_company,
			'from_date': from_date,
			'to_date': to_date,
			'party_type': 'Customer',
			'group_by': 'Group by Voucher (Consolidated)',
			'presentation_currency': 'INR',
			'party': [customer]}
	if isinstance(ledger_filters, str):
		ledger_filters = eval(ledger_filters)
	if 'customer' in ledger_filters:
		ledger_filters['party'] = [ledger_filters['customer']]
		ledger_filters.pop('customer')
	if 'party' in ledger_filters:
		col, data = get_gl_entries_via_api(ledger_filters)
		letterhead_doc = frappe.get_doc("Letter Head", {"is_default": 1})
		ledger_filters['letter_head'] = letterhead_doc.content
		base_template_path = "frappe/www/printview.html"
		template_path = "essdee/essdee/report/party_ledger/party_ledger.html"
		if data:
			html = frappe.render_template(template_path, \
				{"filters": ledger_filters, "data": data})
			html = frappe.render_template(base_template_path, {"body": html, \
				"css": get_print_style(), "title": "Statement For " + ledger_filters['party'][0]})
			return image_conversion(html)

def image_conversion(html):
	soup = BeautifulSoup(html)
	for img in soup.find_all('img'):
		img_url = img.get('src')
		img_path = img_url.split('/')
		if img_path[1] == "private":
			img_url = get_site_path(*img_path)
		elif img_path[1] == "files":
			img_url = get_site_path("public", *img_path)
		else:
			continue
		ext = img_url.split('.')[-1]
		encoded = base64.b64encode(open(img_url, 'rb').read()).decode('utf-8')
		prefix = f'data:image/{ext};base64,'
		img.attrs['src'] = prefix + encoded
	return (str(soup))
