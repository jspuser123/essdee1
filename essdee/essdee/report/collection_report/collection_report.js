// Copyright (c) 2016, Aerele Technologies Pvt Ltd and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Collection Report"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"reqd": 1,
			"default": frappe.defaults.get_user_default("Company"),
			"read_only": 1
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1,
			"width": "60px"
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1,
			"width": "60px"
		},
		{
			"fieldname":"customer_group",
			"label": __("Customer Group"),
			"fieldtype": "Link",
			"options": "Customer Group",
			get_data: function(txt) {
				return frappe.db.get_link_options('Customer Group', txt);
			}
		},
		{
			"fieldname":"show_tcs_eligible",
			"label": __("Show TCS Eligible"),
			"fieldtype": "Check",
			"default": 0,
			"width": "160px"
		},
		{
			"fieldname":"threshold_amount",
			"label": __("Threshold Amount"),
			"fieldtype": "Float",
			"req": 1,
			"default": "5000000",
			"depends_on": 'eval:doc.show_tcs_eligible==1'
		}
	]
};