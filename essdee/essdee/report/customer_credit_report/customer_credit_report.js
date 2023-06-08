// Copyright (c) 2023, Aerele Technologies Pvt Ltd and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Customer Credit Report"] = {
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
			"fieldname":"customer_group",
			"label": __("Customer Group"),
			"fieldtype": "Link",
			"options": "Customer Group",
			get_data: function(txt) {
				return frappe.db.get_link_options('Customer Group', txt);
			},
        },
		{
            fieldname: 'period',
            label: __('period'),
            fieldtype: 'Data',
			default:'12',
   
        },
	]
};

