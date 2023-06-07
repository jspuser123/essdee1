# Copyright (c) 2023, Aerele Technologies Pvt Ltd and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from erpnext.accounts.report.accounts_receivable.accounts_receivable import execute as execute_account_receivable
from essdee.essdee.report.party_outstanding.party_outstanding import calculate_avg_days
from frappe.utils import today, add_to_date,cint,now,getdate
from datetime import datetime
from dateutil.relativedelta import relativedelta

def execute(filters=None):
	columns, data = [], []
	f1=filters
	col1= [{
		'fieldname': 'customer',
		'label': ('Customer'),
		'fieldtype': 'Data',
		},
		{
		'fieldname': 'avg_payment_days',
		'label': ('Avg Payment Days'),
		'fieldtype': 'Date',
		},
		{
		'fieldname': 'payment_pending_days',
		'label': ('Payment Pending Days'),
		'fieldtype': 'Data',
		},
		{
		'fieldname': 'address',
		'label': ('City'),
		'fieldtype': 'Data',
		},
		{
		'fieldname': 'total_outstating_amount',
		'label': ('Total Outstating'),
		'fieldtype': 'Data',
		},
		{
		'fieldname': '0_30',
		'label': ('0-30'),
		'fieldtype': 'Data',
		},
		{
		'fieldname': '31_60',
		'label': ('31-60'),
		'fieldtype': 'Data',	
		},
		{
		'fieldname': '61_90',
		'label': ('61-90'),
		'fieldtype': 'Data',
		},
		{
		'fieldname': '91_120',
		'label': ('91-120'),
		'fieldtype': 'Data',
		},
		{
		'fieldname': '120_above',
		'label': ('120-above'),
		'fieldtype': 'Data',
		},
		{
		'fieldname': 'previous_period',
		'label':('Previous Period'),
		'fieldtype': 'Data',
		},
		{
		'fieldname': 'current_period',
		'label':('Current Period'),
		'fieldtype': 'Data',
		}]
	columns +=col1
	t=today()
	from_date1=(datetime.strptime(t, '%Y-%m-%d') - relativedelta(months=int(f1['period']))).strftime('%Y-%m-%d')
	fil={
		'company':f1['company'],
		'report_date':cint(t),
		'ageing_based_on':'Posting Date',
		'range1':'30',
		'range2':'60',
		'range3':'90',
		'range4':'120',
		'customer_group':f1['customer_group'],
		'period':f1['period'],
		'collection_days':'7',
		'late_payment_age':'30',
		'from_date':from_date1
		}
	customer_list = [customer['name'] for customer in frappe.get_list('Customer',{'customer_group':f1['customer_group']})]
	avg_days = calculate_avg_days(fil, customer_list)		
	slinv_list = frappe.get_list('Sales Invoice', {'status': ['in',['Credit Note Issued','Submitted','Paid','Partly Paid','Unpaid','Unpaid and Discounted','Partly Paid and Discounted','Overdue and Discounted','Overdue','Internal Transfer',]],'customer_group':f1['customer_group']},['customer','status','posting_date'])
	for customer in customer_list:
		col = detail = c = d = e = f = None
		fil['customer'] = customer
		col, detail, c, d, e, f = execute_account_receivable(fil)		
		city = frappe.db.get_value('Address', {"address_title":customer}, 'city')
		maxarry=[]
		total_out_amt = r1 = r2 = r3 = r4 = r5 = total = payment_pending = current_period = previous_period = 0 	
		for d in detail:
			total_out_amt += d['outstanding']
			r1+=d['range1']
			r2+=d['range2']
			r3+=d['range3']
			r4+=d['range4']
			r5+=d['range5']
			total+=d['invoice_grand_total']	
			current=getdate(today())
			if d['posting_date'].year == current.year:
				current_period =total
			elif d['posting_date'].year < current.year:
				previous_period=total
		for slinv in slinv_list:
			if slinv['customer'] ==customer:		
				if 'Completed' == slinv.status:
					payment_pending=0
				else:
					maxarry.append(getdate(t)-slinv.posting_date)
		if maxarry:
			avg_pending=max(maxarry)
			payment_pending=avg_pending.days					
		row ={
				'customer':customer,
				'avg_payment_days': cint(avg_days[customer]) if customer in avg_days else 0,
				'payment_pending_days':payment_pending,	
				'total_outstating_amount':cint(total_out_amt),
				'address':city,
				'0_30':r1,
				'31_60':r2,
				'61_90':r3,
				'91_120':r4,
				'120_above':r5,
				'previous_period':previous_period,
				'current_period':current_period 
				}
		data.append(row)
			
	return columns, data
