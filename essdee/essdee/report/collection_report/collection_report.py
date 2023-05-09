# Copyright (c) 2013, Aerele Technologies Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from erpnext.accounts.utils import get_fiscal_year
import itertools

def execute(filters=None):
	columns, data = [], []
	columns += [{'label': 'Customer', 'fieldname': 'customer', 'fieldtype': 'Link', 'options': 'Customer', 'width': 180},
	{'label': 'Total Collection Amount', 'fieldname': 'total_collection_amount', 'fieldtype': 'Currency', 'options': 'currency', 'width': 180}]
	columns, data = get_data(columns, data, filters)
	return columns, data

def get_data(columns, data, filters):
	data =[]
	threshold_amount = filters['threshold_amount'] if 'threshold_amount' in filters and filters['threshold_amount'] else 0
	account_list = [ account['name'] for account in frappe.get_list('Account', {'account_type': ['in', ['Bank', 'Cash']]})]
	if 'customer_group' in filters and filters['customer_group']:
		customer_list = [customer['name'] for customer in frappe.get_list('Customer',{'customer_group':filters['customer_group']})]
	else:
		customer_list = [customer['name'] for customer in frappe.get_list('Customer')]

	if 'show_tcs_eligible' in filters:
		columns +=[
		{'label': 'TCS Eligible Amount', 'fieldname': 'tcs_eligible_amount', 'fieldtype': 'Currency', 'options': 'currency', 'width': 180},
		{'label': 'Total FY Collection Amount (Till Date)', 'fieldname': 'total_fy_collection_amount', 'fieldtype': 'Currency', 'options': 'currency', 'width': 180},
		{'label': 'Total FY Collection Amount (Before Start Date)', 'fieldname': 'total_fy_collection_before_start_date', 'fieldtype': 'Currency', 'options': 'currency', 'width': 180},
		{'label': 'PAN', 'fieldname': 'pan', 'fieldtype': 'Data', 'width': 180}]
		from_year = get_fiscal_year(filters.from_date)[0]
		to_year = get_fiscal_year(filters.to_date)[0]
		if from_year != to_year:
			frappe.throw("From Date and To Date lies in different Fiscal Year")
		fiscal_year_values = frappe.db.get_values('Fiscal Year', {'name': from_year},['year_start_date', 'year_end_date'])
		fy_based_entries = frappe.db.get_all('Payment Entry',filters=[['posting_date','>=',fiscal_year_values[0][0]],['posting_date','<=',filters.to_date],['docstatus','=',1],['party','in',customer_list], ['party_type','=','Customer'], ['paid_to', 'in', account_list]],fields=['paid_amount', 'party'], order_by = 'party')
		fy_entries_before_start_date = frappe.db.get_all('Payment Entry',filters=[['posting_date','>=',fiscal_year_values[0][0]], ['posting_date','<',filters.from_date],['docstatus','=',1],['party','in',customer_list], ['party_type','=','Customer'], ['paid_to', 'in', account_list]],fields=['paid_amount', 'party'], order_by = 'party')
	entries = frappe.db.get_all('Payment Entry',filters=[['posting_date','>=',filters['from_date']],['posting_date','<=',filters['to_date']],['party','in',customer_list],['docstatus','=',1],['party_type','=','Customer'], ['paid_to', 'in', account_list]],fields=['paid_amount','party'], order_by = 'party')
	for key, group in itertools.groupby(entries, key=lambda x: (x['party'])):
		row = {'customer': key}
		total_collection_amt = sum(row['paid_amount'] for row in group)
		if total_collection_amt:
			row['total_collection_amount'] = total_collection_amt
		if 'show_tcs_eligible' in filters:
			row['pan'] = get_pan_number(key)
			total_fy_collection_amt = sum(entry['paid_amount'] for entry in fy_based_entries if entry['party'] == key)
			total_fy_collection_before_start_date = sum(entry['paid_amount'] for entry in fy_entries_before_start_date if entry['party'] == key)
			if total_fy_collection_amt and total_fy_collection_amt > threshold_amount:
				row['total_fy_collection_amount']= total_fy_collection_amt
				row['total_fy_collection_before_start_date']= total_fy_collection_before_start_date
				if total_fy_collection_before_start_date >= threshold_amount:
					row['tcs_eligible_amount'] = total_collection_amt
				else:
					row['tcs_eligible_amount'] = total_collection_amt - (threshold_amount - total_fy_collection_before_start_date )
			else:
				continue
		if len(row) > 1:
			data.append(row)
	return columns,data

def get_pan_number(customer):
	pan_number = None
	customer_gstin = frappe.db.sql("""select
		`tabAddress`.gstin
	from
		`tabAddress`, `tabDynamic Link`
	where
		`tabAddress`.is_primary_address = 1 and
		`tabDynamic Link`.parent = `tabAddress`.name and
		`tabDynamic Link`.parenttype = 'Address' and
		`tabDynamic Link`.link_doctype = 'Customer' and
		`tabDynamic Link`.link_name = %(customer)s""", {"customer": customer})
	if customer_gstin and customer_gstin[0][0]:
		pan_number = customer_gstin[0][0][2:-3]
	else: 
		pan_number = frappe.db.get_value('Customer', customer, 'tax_id')
	return pan_number