# Copyright (c) 2021, Aerele Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from six import string_types
import json
import erpnext
from erpnext.accounts.report.financial_statements import filter_accounts, get_accounts

class SDTDSPercentageSettings(Document):
	pass

@frappe.whitelist()
def fetch_all_expense_head(tds_mapping):
	if isinstance(tds_mapping, string_types):
		tds_mapping = json.loads(tds_mapping)
	
	accounts = get_accounts(erpnext.get_default_company(), 'Expense')
	accounts, accounts_by_name, parent_children_map = filter_accounts(accounts)
	
	new_tds_mapping = []
	final_tds_mapping = {}
	
	for row in accounts:
		if not row['is_group']:
			new_tds_mapping.append({'account_head': row['name']})
	
	for row in tds_mapping:
		if 'account_head' in row:
			final_tds_mapping[row['account_head']] = [row['tds_for_individual'], row['tds_for_firm']]
	
	for acc in new_tds_mapping:
		if acc['account_head'] in final_tds_mapping:
			acc['tds_for_individual'] = final_tds_mapping[acc['account_head']][0]
			acc['tds_for_firm'] = final_tds_mapping[acc['account_head']][1]
	
	return new_tds_mapping
