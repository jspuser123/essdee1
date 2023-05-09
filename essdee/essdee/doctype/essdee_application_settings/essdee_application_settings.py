# -*- coding: utf-8 -*-
# Copyright (c) 2020, Aerele Technologies Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext, json
from frappe import _, msgprint
from frappe.model.document import Document
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
import requests
from frappe.utils import now_datetime, time_diff, flt, cint, nowdate
from six import string_types
from erpnext.regional.india.utils import get_gst_accounts
from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals
from erpnext.accounts.party import get_dashboard_info
from erpnext.accounts.utils import get_fiscal_year

class EssdeeApplicationSettings(Document):
	pass
def create_custom_field(update=True):
	custom_fields = {
		'Prepared Report': [
				{
				"fieldname": "send_to_telegram",
				"fieldtype": "Check",
				"label": "Send To Telegram",
				"insert_after": "report_end_time",
				"read_only": True
				}
			],
		'Sales Invoice': [
			{
				"fieldname": "sd_discounts",
				"fieldtype": "Table",
				"label": "Essdee Discounts",
				"insert_after": "taxes",
				"options": "SD Sales Invoice Discount"
			}
		]
		}
	create_custom_fields(custom_fields, ignore_validate=frappe.flags.in_patch, update=update)

def set_field_values(doc, action):
	if action == 'before_insert':
		doc.irn_cancelled = 0
		doc.eway_bill_cancelled = 0
		doc.irn = None
		doc.ewaybill = None
		doc.signed_qr_code = None
		doc.qrcode_image = None

def validate_zero_rate(doc, action):
	if action == "on_submit":
		settings = frappe.get_single('Essdee Application Settings')
		if settings.enable_zero_rate:
			zero_rate_items = frappe.get_list('Sales Invoice Item', filters = {'parent': doc.name,'rate': 0}, fields=['idx', 'item_name'])
			exception_items_list = frappe.get_list('SD Exception Item', 'item_name')
			exception_items_list = [d['item_name'] for d in exception_items_list]
			index_list=[]
			for item in zero_rate_items:
				if item['item_name'] not in exception_items_list:
					index_list.append(item['idx'])
			if index_list:
				zero_rate_items_list = ','.join([str(item) for item in sorted(index_list)])
				frappe.throw(_(f'Items with Zero Rate Found at Row(s): {zero_rate_items_list}'))
	
		if settings.allow_only_negative_discount_values and not doc.is_return:
			positive_discount_values = []
			gst_accounts = get_gst_accounts(doc.company)
			gst_accounts_list = [d for accounts in gst_accounts.values() for d in accounts if d]
			for row in doc.taxes:
				if row.account_head in gst_accounts_list:
					break
				elif row.tax_amount > 0:
					positive_discount_values.append(str(row.idx))
			if positive_discount_values:
				positive_discount_values = ','.join(positive_discount_values)
				frappe.throw(_(f'Sales Taxes and Charges with Non-Negative Discounts Found at Row(s): {positive_discount_values}'))

@frappe.whitelist()
def get_special_discount(doc):
	sales_invoice = doc
	if not frappe.get_single('Essdee Application Settings').enable_special_discounts:
		return 0

	exception_list = frappe.get_single('Essdee Application Settings').exceptions
	for exception in exception_list:
		if doc.customer == exception.customer or doc.transport == exception.transporter:
			return exception.special_discount

	from_gstin = sales_invoice.company_gstin
	customer_gstin = sales_invoice.customer_gstin
	billing_address_gstin = sales_invoice.billing_address_gstin

	if not customer_gstin or not billing_address_gstin:
		return 0
	
	transport = sales_invoice.transport

	previous_freight_amt = frappe.db.sql(f"select number_of_cartons, freight_amount from `tabSales Invoice` \
		where company_gstin = \'{from_gstin}\' and \
			(billing_address_gstin = \'{billing_address_gstin}\' or customer_gstin = \'{customer_gstin}\')  and \
			transport = \'{transport}\' and lr_number != '' \
		order by modified desc  limit 1", as_dict=True)

	if not len(previous_freight_amt):
		return 0
	
	special_discount = (previous_freight_amt[0]['freight_amount']/previous_freight_amt[0]['number_of_cartons']) * sales_invoice.number_of_cartons

	return special_discount

def add_special_discount(doc, action):
	special_discount_amount = get_special_discount(doc)
	company_abbr = frappe.db.get_value("Company", erpnext.get_default_company(), "abbr")
	for tax in doc.taxes:
		if tax.account_head == f'Special Discount - {company_abbr}':
			if not tax.tax_amount:
				tax.tax_amount = -(special_discount_amount)

@frappe.whitelist()
def sync_data():
	customer_list = frappe.db.get_all('Customer', ["name", "customer_group", "disabled","city"], as_list=True)
	customer_details = get_customer_details_list(customer_list)
	if customer_details:
		post_request(customer_details)

@frappe.whitelist()
def sync_with_partner(customer):
	customer_list = frappe.db.get_all('Customer', ["name", "customer_group", "disabled","city"], {"name": customer}, as_list=True)
	customer_details = get_customer_details_list(customer_list)
	result = post_request(customer_details)
	if not result:
		frappe.throw(_('Failed to sync with the partner document'))
	msgprint(_('Successfully synced with the partner document'))

def get_customer_details_list(customer_list):
	customer_details_list = []
	for customer in customer_list:
		contacts = frappe.db.get_values(
			"Dynamic Link",
			{
				"parentfield": "links",
				"parenttype": "Contact",
				"link_doctype": "Customer",
				"link_name": customer[0]
			},
			"parent")
		if contacts:
			contacts = [contact[0] for contact in contacts]
			mobile_numbers = frappe.db.get_values('Contact', {"name": ["in", contacts]}, 'mobile_no','city')
			mobile_numbers = list(mobile_number[0] for mobile_number in mobile_numbers if mobile_number[0] and len(mobile_number[0])==10)
		else:
			mobile_numbers = []
		customer_details_list.append({
				"name": customer[0],
				"customer_group": customer[1],
				"mobile_numbers": mobile_numbers,
				"disabled": customer[2],
				"city": customer[3]
		})
	return customer_details_list

def post_request(customer_details):
	essdee_partners_site_url = frappe.get_single('Essdee Application Settings').essdee_partners_site_url
	url = f"{essdee_partners_site_url}/api/method/essdee_partners_api.essdee_partners_api.doctype.partners.partners.sync_partners_with_customers"
	api_key = frappe.get_single('Essdee Application Settings').api_key
	api_secret = frappe.get_single('Essdee Application Settings').api_secret
	authorization = "token "+ api_key + ":" + api_secret
	data = {
		"customer_details" : json.dumps(customer_details)
	}
	headers = {
		'Accept': 'application/json',
		'Authorization': authorization
	}
	response = requests.post(url, headers=headers, data=data)
	if not response.status_code == 200:
		frappe.log_error("Time: "+now_datetime().__str__()[:-7]+" | code: " + str(response.status_code)+ " | response: " + response.text, "Sync Status")
		return False
	return True

def time_diff_in_minutes(string_ed_date, string_st_date):
	return time_diff(string_ed_date, string_st_date).total_seconds() / 60

def set_tcs(doc, action):
	if action == "validate":
		settings = frappe.get_single("Essdee Application Settings")
		if not cint(settings.enable_tcs):
			return
		if doc.customer in [x.customer for x in settings.tcs_exception_customers]:
			return
		if doc.docstatus != 0:
			return
		if len(doc.taxes) < 1:
			return
		if settings.tcs_account in [x.account_head for x in doc.taxes]:
			return

		info = get_dashboard_info("Customer", doc.customer)
		customer_turnover = 0
		for company_info in info:
			if company_info['company'] == doc.company:
				customer_turnover = company_info['billing_this_year']
		if settings.tcs_trigger_amount >= customer_turnover + flt(doc.rounded_total):
			return
		tcs_row = frappe.new_doc('Sales Taxes and Charges')
		tcs_row.update({
						"charge_type": "On Previous Row Total",
						"row_id": str(len(doc.taxes)),
						"account_head": settings.tcs_account,
						"rate": settings.tcs_percentage,
						"description": settings.tcs_invoice_description,
						"parenttype": "Sales Invoice",
						"parentfield": "taxes",
						"parent": doc.name,
						"idx": len(doc.taxes) + 1
					})
		doc.taxes.append(tcs_row)
		calculate_taxes_and_totals(doc)

def set_tds(doc, action):
	if action == "validate":
		settings = frappe.get_single("Essdee Application Settings")
		if not cint(settings.enable_tds):
			return
		if doc.docstatus != 0:
			return
		if settings.tds_account in [x.account_head for x in doc.taxes]:
			return

		if not check_tds_threshold(doc.supplier, doc.company, doc.rounded_total, settings.tds_trigger_amount, doc.posting_date) and flt(doc.tds_percent) == 0:
			return	
		tds_row = frappe.new_doc('Purchase Taxes and Charges')
		rate = doc.tds_percent
		if flt(settings.tds_percentage) > flt(rate):
			rate = settings.tds_percentage
		tds_row.update({
						"charge_type": "On Net Total",
						"account_head": settings.tds_account,
						"rate": rate,
						"description": settings.tds_invoice_description,
						"category": "Total",
						"add_deduct_tax": "Deduct",
						"parenttype": "Purchase Invoice",
						"parentfield": "taxes",
						"parent": doc.name,
						"idx": len(doc.taxes) + 1
					})
		doc.taxes.append(tds_row)
		calculate_taxes_and_totals(doc)

def check_tds_threshold(supplier, company, rounded_total, tds_trigger_amount, transaction_date=None):
	# info = get_dashboard_info("Supplier", supplier)
	supplier_turnover = 0
	# for company_info in info:
	# 	if company_info['company'] == company:
	# 		supplier_turnover = company_info['billing_this_year']
	if not transaction_date:
		transaction_date = nowdate()
	current_fiscal_year = get_fiscal_year(transaction_date, as_dict=True)
	doctype = "Purchase Invoice"
	company_wise_grand_total = frappe.get_all(doctype,
		filters={
			'docstatus': 1,
			'supplier': supplier,
			'posting_date': ('between', [current_fiscal_year.year_start_date, current_fiscal_year.year_end_date]),
			'company': company
			},
			group_by="company",
			fields=["company", "sum(grand_total) as grand_total", "sum(base_grand_total) as base_grand_total"]
		)

	if company_wise_grand_total:
		supplier_turnover = flt(company_wise_grand_total[0].get("grand_total"))

	if tds_trigger_amount and tds_trigger_amount < (supplier_turnover + flt(rounded_total)):
		return True
	return False
