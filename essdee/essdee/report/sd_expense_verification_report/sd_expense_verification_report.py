# Copyright (c) 2013, Aerele Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import  _
from frappe.utils import flt, cint
from erpnext.accounts.report.financial_statements import get_accounts
from erpnext.accounts.report.general_ledger.general_ledger import get_gl_entries
import re
from past.builtins import cmp
import functools
from essdee.essdee.doctype.essdee_application_settings.essdee_application_settings import check_tds_threshold

value_fields = ('calculated_tds', 'actual_tds', 'difference_in_tds', 'credit', 'debit')
settings = frappe.get_single("Essdee Application Settings")

def execute(filters=None):
	columns, data = [], []
	columns = get_columns(filters)
	accounts = get_accounts(filters['company'], 'Expense')
	if not accounts:
		return columns, data

	filters['group_by'] = "Group by Voucher"
	tds_entries = []
	if cint(settings.enable_tds):
		filters['account'] = settings.tds_account
		tds_entries = get_gl_entries(filters)
	for row in accounts:
		if 'is_group' in row and not row['is_group']:
			parent = row['name']
			filters['account'] = row['name']
			gl_entries = get_gl_entries(filters)
			suppliers = []
			other_docs = set()
			for entry in gl_entries:
				against_account = entry['against']
				tds = []
				if entry['voucher_type'] == 'Purchase Invoice' and entry['against'] and frappe.db.exists('Supplier', entry['against']):
					if not entry['against'] in suppliers:
						suppliers.append(entry['against'])

					pan = get_pan_number(entry['against'])
					if pan:
						total_val = entry['debit'] - entry['credit']
						tds = get_tds(pan, filters, tds_entries, entry['voucher_no'], parent, total_val)

					voucher_no = entry['voucher_no']
					accounts.append(frappe._dict({'account_name': voucher_no,
												'name': f'{voucher_no} :: {parent}', 
												'credit': entry['credit'], 
												'debit': entry['debit'] , 
												'parent_account': f'{against_account} :: {parent}', 
												'actual_tds': tds[0] if tds else 0,
												'calculated_tds': tds[1] if tds else 0,
												'tds_percentage': tds[2] if tds else 0,
												'difference_in_tds': tds[3] if tds else 0,
												'is_invoice':1}))

				else:
					other_docs.add(entry['voucher_type'])
			
					voucher_type = entry['voucher_type']
					accounts.append(frappe._dict({'account_name': entry['against'], 'name': f'{against_account} :: {voucher_type} :: {parent}', 'credit': entry['credit'], 'debit': entry['debit'] , 'parent_account': f'{voucher_type} :: {parent}'}))
			
			for val in suppliers:
				pan = get_pan_number(val)
				dict_val = {'name': f'{val} :: {parent}',
							'parent_account': parent, 
							'account_name':  val,
							'is_supplier': 1}
				if pan:
					dict_val['pan'] = pan
					if pan[3] in ['P', 'H']:
						tds_percentage = frappe.db.get_value('SD TDS Mapping',{'account_head': parent},'tds_for_individual')
					else:
						tds_percentage = frappe.db.get_value('SD TDS Mapping',{'account_head': parent},'tds_for_firm')
					dict_val['tds_percentage'] = tds_percentage
				accounts.append(frappe._dict(dict_val))
			
			for doc in other_docs:
				accounts.append(frappe._dict({'account_name': doc, 'name': f'{doc} :: {parent}', 'parent_account': parent, 'is_other_doc': 1}))


	accounts, accounts_by_name, parent_children_map = filter_accounts(accounts)
	accumulate_values_into_parents(accounts, accounts_by_name)

	data = []
	for d in accounts:
		# add to output
		has_value = False
		if 'is_supplier' in d and d.is_supplier and not 'show_supplier_breakup' in filters:
			continue
		if not 'show_invoices' in filters and 'is_invoice' in d and d.is_invoice:
			continue
		new_row = {
			"is_group": d.is_group,
			"account": _(d.name),
			"parent_account": _(d.parent_account) if d.parent_account else '',
			"indent": flt(d.indent),
			"account_name":  _(d.account_name) or _(d.name),
			"credit": d.credit,
			"debit": d.debit
		}
		if 'show_tds' in filters:
			new_row.update({"calculated_tds": d.calculated_tds,
						"actual_tds": d.actual_tds,
						"difference_in_tds": d.difference_in_tds})
			if 'tds_percentage' in d:
				new_row['tds_percentage'] = d.tds_percentage
			if 'pan' in d:
				new_row["pan"]= d.pan
		row = frappe._dict(new_row)
		row["has_value"] = has_value
		if new_row['credit'] or new_row['debit']:
			data.append(row)

	return columns, data

def accumulate_values_into_parents(accounts, accounts_by_name):
	for d in reversed(accounts):
		if d.parent_account:
			for key in value_fields:
				if not key in accounts_by_name[d.parent_account]:
					accounts_by_name[d.parent_account][key] = 0
				if not key in d:
					d[key] = 0
				accounts_by_name[d.parent_account][key] += d[key]

def get_columns(filters):
	columns = [
		{
		"fieldname": "account",
		"label": _("Account"),
		"fieldtype": "Link",
		"options": "Account",
		"width": 280
		},
		{
		"fieldname": "debit",
		"label": _("Debit"),
		"fieldtype": "Currency",
		"width": 150
		},
		{
		"fieldname": "credit",
		"label": _("Credit"),
		"fieldtype": "Currency",
		"width": 150
		}
	]
	if filters.get('show_tds'):
		columns += [{
		"fieldname": "pan",
		"label": _("PAN"),
		"fieldtype": "Data",
		"width": 150
		},
		{
		"fieldname": "tds_percentage",
		"label": _("TDS (%)"),
		"fieldtype": "Float",
		"width": 80
		},
		{
		"fieldname": "calculated_tds",
		"label": _("Calculated TDS"),
		"fieldtype": "Currency",
		"width": 150
		},
		{
		"fieldname": "actual_tds",
		"label": _("Actual TDS"),
		"fieldtype": "Currency",
		"width":150
		},
		{
		"fieldname": "difference_in_tds",
		"label": _("Difference(TDS)"),
		"fieldtype": "Currency",
		"width": 150
		}]
	return columns


def get_gl_entries(filters):
	select_fields = """, debit, credit, debit_in_account_currency,
		credit_in_account_currency """

	order_by_statement = "order by posting_date, account, creation"

	if filters.get("group_by") == _("Group by Voucher"):
		order_by_statement = "order by posting_date, voucher_type, voucher_no"

	gl_entries = frappe.db.sql(
		"""
		select
			name as gl_entry, posting_date, account, party_type, party,
			voucher_type, voucher_no, cost_center, project,
			against_voucher_type, against_voucher, account_currency,
			remarks, against, is_opening {select_fields}
		from `tabGL Entry`
		where company=%(company)s {conditions}
		{order_by_statement}
		""".format(
			select_fields=select_fields, conditions=get_conditions(filters),
			order_by_statement=order_by_statement
		),
		filters, as_dict=1)

	return gl_entries


def get_conditions(filters):
	conditions = []
	if filters.get("account"):
		lft, rgt = frappe.db.get_value("Account", filters["account"], ["lft", "rgt"])
		conditions.append("""account in (select name from tabAccount
			where lft>=%s and rgt<=%s and docstatus<2)""" % (lft, rgt))

	conditions.append("posting_date >=%(from_date)s")

	conditions.append("(posting_date <=%(to_date)s)")

	return "and {}".format(" and ".join(conditions)) if conditions else ""

def get_pan_number(supplier):
	pan_number = None
	supplier_gstin = frappe.db.sql("""select
		`tabAddress`.gstin
	from
		`tabAddress`, `tabDynamic Link`
	where
		`tabDynamic Link`.parent = `tabAddress`.name and
		`tabDynamic Link`.parenttype = 'Address' and
		`tabDynamic Link`.link_doctype = 'Supplier' and
		`tabDynamic Link`.link_name = %(supplier)s""", {"supplier": supplier})
	if supplier_gstin and supplier_gstin[0][0]:
		pan_number = supplier_gstin[0][0][2:-3]
	else: 
		pan_number = frappe.db.get_value('Supplier', supplier, 'tax_id')
	return pan_number

def filter_accounts(accounts, depth=20):
	parent_children_map = {}
	accounts_by_name = {}
	for d in accounts:
		accounts_by_name[d.name] = d
		parent_children_map.setdefault(d.parent_account or None, []).append(d)

	filtered_accounts = []

	def add_to_list(parent, level):
		if level < depth:
			children = parent_children_map.get(parent) or []

			other_doc_children = []
			for child in children[::]:
				if child.is_other_doc:
					other_doc_children.append(child)
					children.remove(child)

			sort_accounts(children, is_root=True if parent==None else False)

			children += other_doc_children
			for child in children:
				child.indent = level
				filtered_accounts.append(child)
				add_to_list(child.name, level + 1)

	add_to_list(None, 0)

	return filtered_accounts, accounts_by_name, parent_children_map

def sort_accounts(accounts, is_root=False, key="name"):

	def compare_accounts(a, b):
		if re.split('\W+', a[key])[0].isdigit():
			# if chart of accounts is numbered, then sort by number
			return cmp(a[key], b[key])
		elif is_root:
			if a.root_type == "Income" and b.root_type == "Expense":
				return -1
		else:
			# sort by key (number) or name
			return cmp(a[key], b[key])
		return 1

	accounts.sort(key = functools.cmp_to_key(compare_accounts))

def get_tds(pan, filters, tds_entries, inv_no, parent, total_val):
	inv_doc = frappe.get_doc('Purchase Invoice', inv_no)
	expense_head_list = []

	if frappe.db.get_value('SD TDS Mapping',{'account_head': parent},'ignore_for_tds'):
		return
	
	tds_trigger_amount = frappe.db.get_value('SD TDS Mapping', {'parenttype':'SD TDS Percentage Settings','account_head': parent},'threshold')
	if not check_tds_threshold(inv_doc.supplier, filters['company'], inv_doc.rounded_total, tds_trigger_amount, inv_doc.posting_date) and \
		flt(inv_doc.tds_percent) ==0:
		return 
	
	for row in inv_doc.items:
		if row.expense_account:
			expense_head_list.append(row.expense_account)
	
	if expense_head_list:
		if not parent == expense_head_list[0]:
			return 
	
	actual_tds = sum([ (row['credit'] - row['debit']) if row['voucher_no'] == inv_no else 0 for row in tds_entries])	

	if pan[3] in ['P', 'H']:
		tds_percentage = frappe.db.get_value('SD TDS Mapping',{'account_head': parent},'tds_for_individual')
	else:
		tds_percentage = frappe.db.get_value('SD TDS Mapping',{'account_head': parent},'tds_for_firm')

	calculated_tds = (total_val)* (tds_percentage/100)
	difference_in_tds = calculated_tds - actual_tds
	
	return [actual_tds, calculated_tds, tds_percentage, difference_in_tds]