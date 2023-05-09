# Copyright (c) 2013, Aerele Technologies Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.www.printview import get_print_style
from frappe.utils import today, add_to_date, now_datetime, comma_and, get_link_to_form, cint
from erpnext.accounts.report.accounts_receivable.accounts_receivable import execute as execute_account_receivable
from essdee.essdee.report.party_outstanding.party_outstanding import calculate_avg_days
from essdee.essdee.report.agent_outstanding.agent_outstanding import get_agent_outstanding_print_html
import json
from frappe.desk.query_report import get_prepared_report_result, get_report_doc, background_enqueue_run
from essdee.essdee.doctype.essdee_application_settings.essdee_application_settings import time_diff_in_minutes
from frappe import _, msgprint
from frappe.utils.pdf import get_pdf
from frappe.core.page.background_jobs.background_jobs import get_info
from frappe.utils.background_jobs import enqueue
from frappe.utils.user import get_users_with_role

def execute(filters=None):
	columns, data = [], []
	if not 'customer_group' in filters:
		customer_group = frappe.get_value('User Permission',{'user':frappe.session.user,'allow':'Customer Group'},'for_value')
		if not customer_group:
			return columns, data 
		filters['customer_group'] = customer_group
	data = get_data(data, filters)
	columns = [{'label': 'Customer', 'fieldname': 'customer', 'fieldtype': 'Link', 'options': 'Customer', 'width': 180},
	{'label': 'City', 'fieldname': 'city', 'fieldtype': 'Data', 'options': None, 'width': 180},
	{'label': 'Total Outstanding Amount', 'fieldname': 'total_out_amt', 'fieldtype': 'Currency', 'options': 'currency', 'width': 180},
	{'label': 'Late Payment', 'fieldname': 'late_payment', 'fieldtype': 'Currency', 'options': 'currency', 'width': 180},
	{'label': 'Previous Week Collection', 'fieldname': 'previous_week_collection', 'fieldtype': 'Currency', 'options': 'currency', 'width': 180},
	{'label': 'Avg Days', 'fieldname': 'avg_days', 'fieldtype': 'Int', 'options': None, 'width': 180}]
	return columns, data


def get_data(data, filters):
	customer_list = [customer['name'] for customer in frappe.get_list('Customer',{'customer_group':filters['customer_group']})]
	avg_days = calculate_avg_days(filters, customer_list)
	for customer in customer_list:
		filters['customer'] = customer
		columns = detail = c = d = e = f = None
		columns, detail, c, d, e, f = execute_account_receivable(filters)
		late_payment = 0
		total_out_amt = 0
		for d in detail:
			total_out_amt += d['outstanding']
			if d['age'] > filters['late_payment_age']:
				late_payment += d['outstanding']
		previous_week_collection = calculate_collection_amt(filters, customer)
		if [late_payment, total_out_amt, previous_week_collection].count(0)==3:
			continue
		city = ''
		addresses = frappe.db.get_values("Dynamic Link",{"parentfield": "links","parenttype": "Address","link_doctype": "Customer","link_name": customer},"parent")
		if addresses:
			city = frappe.db.get_value('Address', {"name": addresses[-1][0]}, 'city')
		data.append({'customer':customer,
				'city':city, 
				'total_out_amt': cint(total_out_amt),
				'late_payment': cint(late_payment),
				'previous_week_collection': cint(previous_week_collection),
				'avg_days': cint(avg_days[customer]) if customer in avg_days else 0})
	data = sorted(data, key = lambda i: (i['late_payment'], i['total_out_amt']), reverse=True)
	return data
def calculate_collection_amt(filters, customer):
	if 'report_date' in filters and filters['report_date']:
		from_date = add_to_date(filters['report_date'], days=-filters['collection_days'])
		to_date = add_to_date(filters['report_date'], days=-1)
		entries = frappe.db.get_all('Payment Entry',filters=[['posting_date','Between',[from_date, to_date]],['party','=',customer],['docstatus','=',1],['party_type','=','Customer']],fields=['paid_amount'])
		return sum(entry['paid_amount'] for entry in entries)
	

@frappe.whitelist()
def get_agent_late_payment_html(customer_group=None, late_payment_filters=None, prepared_report_name=''):

	user = frappe.session.user
	if not late_payment_filters:
		default_company = frappe.defaults.get_user_default("Company")
		late_payment_filters = {'company': default_company,
		'report_date': today(),
		'ageing_based_on': 'Posting Date',
		'range1': 30,
		'range2': 60,
		'range3': 90,
		'range4': 120,
		'customer_group': customer_group}
	if isinstance(late_payment_filters, str):
		late_payment_filters = eval(late_payment_filters)

	if 'customer_group' in late_payment_filters:
		report = get_report_doc('Agent Late Payment')
		data = get_prepared_report_result(report, late_payment_filters, prepared_report_name, user)
		prepared_report_doc = data['doc']

		base_template_path = "frappe/www/printview.html"
		template_path = "essdee/essdee/report/agent_late_payment/agent_late_payment.html"
		if 'result' in data:
			data = data['result']
			data.pop()
			html = frappe.render_template(template_path, \
					{"filters": late_payment_filters, "data": data, "doc": prepared_report_doc})
			html = frappe.render_template(base_template_path, {"body": html, \
					"css": get_print_style(), "title": "Statement For " + late_payment_filters['customer_group']})

			return html

@frappe.whitelist()
def background_enqueue_send_reports(action = None, filters = None, prepared_report_name = '', report_name=''):
	user = frappe.session.user
	if not user in get_users_with_role("Accounts Manager") and user != 'Administrator' and action == 'send_all_reports':
		frappe.throw(_("You do not have enough permissions to access this resource. Please contact your manager to get access."))
		return
	if isinstance(filters, str):
		filters = eval(filters)

	bot = frappe.db.get_value('Report Bot Mapping', {'report':report_name},['bot'])
	if not bot:
		settings_page = "Essdee Application Settings"
		frappe.throw(_("No bot found. Kindly map the corresponding bot for report {0} in {1}")
					.format(frappe.bold(_(report_name)),
					get_link_to_form(settings_page, settings_page, frappe.bold(settings_page))))
	enqueued_jobs = [d.get("job_name") for d in get_info()]
	
	if action == 'send_all_reports':
		report_date = filters['report_date']
		job_name = f'{report_name}-{action}-{report_date}'
	
	if action == 'send_single_report':
		customer_group = filters['customer_group']
		report_date = filters['report_date']
		job_name = f'{report_name}-{customer_group}-{report_date}'

	if job_name in enqueued_jobs:
		frappe.throw(
			_("Send reports already in progress. Please wait for sometime.")
		)
	else:
		track_details = {'report_name': report_name, 'filters': filters, 'prepared_report': prepared_report_name}
		enqueue(
			send_reports,
			queue="default",
			timeout=6000,
			event= 'send_reports_to_telegram',
			track_details= track_details,
			job_name= job_name
		)
		frappe.throw(
			_("Send reports job added to the queue. Please check after sometime.")
		)


def send_reports(track_details):
	prepared_report_list = []
	customer_group_list = []
	filters = track_details['filters']

	if 'customer_group' in filters:
		customer_group_list = [{'name':filters['customer_group']}]
	if not customer_group_list:
		customer_group_list = frappe.get_list('Customer Group Mapping', {'parent':'Essdee Application Settings'},'customer_group as name')

	for customer_group in customer_group_list:
		customer_group_name = customer_group['name']
		filters['customer_group'] = customer_group_name
		if track_details['prepared_report']:
			is_already_sent = frappe.db.get_value('Prepared Report',{'name':track_details['prepared_report'], 'status':('!=','Error')},'send_to_telegram')
			if not is_already_sent:
				prepared_report_list.append(track_details['prepared_report'])
		else:
			prepared_report_list.append(create_prepared_report(track_details['report_name'], filters))

		if 'customer' and 'party' in filters:
			filters.pop('customer')
			filters.pop('party')

	for report in prepared_report_list:
		doc = frappe.get_doc('Prepared Report', report)
		doc.send_to_telegram = 1
		doc.save(ignore_permissions=True)
		doc.reload()

def create_prepared_report(report_name, filters):
	report = get_report_doc(report_name)
	data = get_prepared_report_result(report, filters)
	if data['doc'] and not data['doc'].send_to_telegram:
		return data['doc'].name
	track_info = background_enqueue_run(report_name, json.dumps(filters))
	if track_info:
		return track_info['name']

def create_send_document(doc, action):
	if action == 'on_change' and doc.status == 'Completed' and doc.send_to_telegram:
		prepared_doc = frappe.get_doc('Prepared Report', doc.name)
		filters = json.loads(prepared_doc.filters)
		customer_group = filters['customer_group']
		bot = frappe.db.get_value('Report Bot Mapping', {'report':prepared_doc.report_name},['bot'])
		telegram_chat = frappe.db.get_value('Customer Group Mapping', {'customer_group': customer_group},['telegram_chat'])
		if not telegram_chat:
			settings_page = "Essdee Application Settings"
			frappe.log_error(f"Kindly map the corresponding chat for customer group {customer_group} in {settings_page}.", "Telegram chat not found")
		else:
			file_name = create_temp_file(prepared_doc)
			is_file_linked = frappe.db.get_value('Send Document',{'file':file_name,'status':'Queued'})
			if not is_file_linked:
				send_doc = frappe.get_doc({'doctype': 'Send Document',
						'bot':bot,
						'telegram_chat':telegram_chat,
						'file':file_name,
						'status':'Queued',
						'delete_linked_file_after_sent': 1})
				send_doc.save(ignore_permissions=True)
				if send_doc:
					prepared_doc.send_to_telegram = 0
					prepared_doc.save(ignore_permissions=True)
					prepared_doc.reload()


def create_temp_file(doc):
	report_name_mapping = {'Agent Late Payment': 'Late', 'Agent Outstanding': 'Total'}
	report_name = report_name_mapping[doc.report_name]
	customer_group = json.loads(doc.filters)['customer_group']
	file_name = f'{customer_group}-{report_name}.pdf'
	# todo: don't use the same file if found... an one week old file got sent and created a lot of confusions...
	file_exist = frappe.db.get_value('File',{'file_name':file_name},'name')
	content = get_content(doc)
	if not file_exist and content:
		_file = frappe.get_doc({
			"doctype": "File",
			"file_name": file_name,
			"content": content})
		_file.save(ignore_permissions=True)
		file_exist = _file.name
	return file_exist

def get_content(doc):
	if doc.report_name == 'Agent Late Payment':
		orientation = 'Portrait'
		html =  get_agent_late_payment_html(late_payment_filters=doc.filters, prepared_report_name=doc.name)
	else:
		orientation = 'Landscape'
		html =  get_agent_outstanding_print_html(outstanding_filters=doc.filters, prepared_report_name=doc.name)

	return get_pdf(html, {"orientation": orientation})