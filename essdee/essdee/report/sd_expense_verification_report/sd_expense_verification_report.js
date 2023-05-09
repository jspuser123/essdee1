// Copyright (c) 2016, Aerele Technologies Pvt Ltd and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.require("assets/erpnext/js/financial_statements.js", function() {
frappe.query_reports["SD Expense Verification Report"] = {
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
				"reqd": 1
			},
			{
				"fieldname":"to_date",
				"label": __("To Date"),
				"fieldtype": "Date",
				"default": frappe.datetime.get_today(),
				"reqd": 1
			},
			{
				"fieldname":"show_supplier_breakup",
				"label": __("Show Supplier Breakup"),
				"fieldtype": "Check"
			},
			{
				"fieldname":"show_tds",
				"label": __("Show TDS"),
				"fieldtype": "Check"
			},
			{
				"fieldname":"show_invoices",
				"label": __("Show Invoices"),
				"fieldtype": "Check"
			}
	],
	"formatter": function(value, row, column, data, default_formatter) {
		if (data && column.fieldname=="account") {
			value = data.account || value;
			column.link_onclick = "frappe.query_reports['SD Expense Verification Report'].open_general_ledger(" + JSON.stringify(data) + ")";	
			column.is_tree = true;
		}

		value = default_formatter(value, row, column, data);

		if (data && !data.parent_account) {
			value = $(`<span>${value}</span>`);

			var $value = $(value).css("font-weight", "bold");
			if (data.warn_if_negative && data[column.fieldname] < 0) {
				$value.addClass("text-danger");
			}

			value = $value.wrap("<p></p>").parent().html();
		}

		return value;
	},
	"open_general_ledger": function(data) {
		if (!data.account_name) return;
		account_name_arr = data.account.split(' :: ')
		frappe.db.exists("Purchase Invoice", account_name_arr[0]).then(val => {
			if(val)
			{
				frappe.route_options = {
					"account": account_name_arr[1],
					"voucher_no": account_name_arr[0],
					"company": frappe.query_report.get_filter_value('company'),
					"from_date": frappe.query_report.get_filter_value('from_date'),
					"to_date": frappe.query_report.get_filter_value('to_date')
				};
				frappe.set_route("query-report", "General Ledger");
				return
			}

		})
		frappe.db.exists("Supplier", data.account_name).then(exists => {
			if (exists) {
				frappe.route_options = {
					"party": data.account_name,
					"party_type": "Supplier",
					"company": frappe.query_report.get_filter_value('company'),
					"from_date": frappe.query_report.get_filter_value('from_date'),
					"to_date": frappe.query_report.get_filter_value('to_date')
				};
				frappe.set_route("query-report", "General Ledger");
				return
			}
		 else{
		    frappe.db.exists("Account", data.account).then(res => {
				if (res) {
					frappe.route_options = {
						"account": data.account,
						"company": frappe.query_report.get_filter_value('company'),
						"from_date": frappe.query_report.get_filter_value('from_date'),
						"to_date": frappe.query_report.get_filter_value('to_date')
					};
					frappe.set_route("query-report", "General Ledger");
					return
				}
				else{
					frappe.route_options = {
						"account": data.account_name,
						"company": frappe.query_report.get_filter_value('company'),
						"from_date": frappe.query_report.get_filter_value('from_date'),
						"to_date": frappe.query_report.get_filter_value('to_date')
					};
					frappe.set_route("query-report", "General Ledger");
					return
				}
			});	
		}
		});
	},
	"tree": true,
	"name_field": "account",
	"parent_field": "parent_account",
	"initial_depth": 1
};
});
