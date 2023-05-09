// Copyright (c) 2016, Aerele Technologies Pvt Ltd and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Party Ledger"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldtype": "Break",
		},
		{
			"fieldname":"finance_book",
			"label": __("Finance Book"),
			"fieldtype": "Link",
			"options": "Finance Book",
			"hidden": 1
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
			"fieldtype": "Break",
		},
		{
			"fieldname":"account",
			"label": __("Account"),
			"fieldtype": "Link",
			"options": "Account",
			"get_query": function() {
				var company = frappe.query_report.get_filter_value('company');
				return {
					"doctype": "Account",
					"filters": {
						"company": company,
					}
				}
			},
			"hidden": 1
		},
		{
			"fieldname":"voucher_no",
			"label": __("Voucher No"),
			"fieldtype": "Data",
			on_change: function() {
				frappe.query_report.set_filter_value('group_by', "Group by Voucher (Consolidated)");
			},
			"hidden": 1	
		},
		{
			"fieldname":"party_type",
			"label": __("Party Type"),
			"fieldtype": "Link",
			"options": "Party Type",
			"default": "Customer",
			on_change: function() {
				frappe.query_report.set_filter_value('party', "");
			},
			"hidden": 1
		},
		{
			"fieldname":"customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			on_change: () => {
				var customer = frappe.query_report.get_filter_value('customer');
				var company = frappe.query_report.get_filter_value('company');
				if (customer) {
					frappe.db.get_value('Customer', customer, ["tax_id", "customer_name", "payment_terms"], function(value) {
						frappe.query_report.set_filter_value('tax_id', value["tax_id"]);
						frappe.query_report.set_filter_value('customer_name', value["customer_name"]);
						frappe.query_report.set_filter_value('payment_terms', value["payment_terms"]);
					});

					frappe.db.get_value('Customer Credit Limit', {'parent': customer, 'company': company},
						["credit_limit"], function(value) {
						if (value) {
							frappe.query_report.set_filter_value('credit_limit', value["credit_limit"]);
						}
					}, "Customer");
				} else {
					frappe.query_report.set_filter_value('tax_id', "");
					frappe.query_report.set_filter_value('customer_name', "");
					frappe.query_report.set_filter_value('credit_limit', "");
					frappe.query_report.set_filter_value('payment_terms', "");
				}
			}
		},
		{
			"fieldname":"party",
			"label": __("Party"),
			"fieldtype": "MultiSelectList",
			"hidden": 1,
			get_data: function(txt) {
				if (!frappe.query_report.filters) return;

				let party_type = frappe.query_report.get_filter_value('party_type');
				if (!party_type) return;

				return frappe.db.get_link_options(party_type, txt);
			},
			on_change: function() {
				var party_type = frappe.query_report.get_filter_value('party_type');
				var parties = frappe.query_report.get_filter_value('party');

				if(!party_type || parties.length === 0 || parties.length > 1) {
					frappe.query_report.set_filter_value('party_name', "");
					frappe.query_report.set_filter_value('tax_id', "");
					return;
				} else {
					var party = parties[0];
					var fieldname = erpnext.utils.get_party_name(party_type) || "name";
					frappe.db.get_value(party_type, party, fieldname, function(value) {
						frappe.query_report.set_filter_value('party_name', value[fieldname]);
					});

					if (party_type === "Customer" || party_type === "Supplier") {
						frappe.db.get_value(party_type, party, "tax_id", function(value) {
							frappe.query_report.set_filter_value('tax_id', value["tax_id"]);
						});
					}
				}
			}
		},
		{
			"fieldname":"party_name",
			"label": __("Party Name"),
			"fieldtype": "Data",
			"hidden": 1
		},
		{
			"fieldname":"group_by",
			"label": __("Group by"),
			"fieldtype": "Select",
			"options": ["", __("Group by Voucher"), __("Group by Voucher (Consolidated)"),
				__("Group by Account"), __("Group by Party")],
			"default": __("Group by Voucher (Consolidated)"),
			"hidden": 1
		},
		{
			"fieldname":"tax_id",
			"label": __("Tax Id"),
			"fieldtype": "Data",
			"hidden": 1
		},
		{
			"fieldname": "presentation_currency",
			"label": __("Currency"),
			"fieldtype": "Select",
			"options": erpnext.get_presentation_currency_list(),
			"default": "INR",
			"hidden": 1
		},
		{
			"fieldname":"cost_center",
			"label": __("Cost Center"),
			"fieldtype": "MultiSelectList",
			get_data: function(txt) {
				return frappe.db.get_link_options('Cost Center', txt);
			},
			"hidden": 1
		},
		{
			"fieldname":"project",
			"label": __("Project"),
			"fieldtype": "MultiSelectList",
			get_data: function(txt) {
				return frappe.db.get_link_options('Project', txt);
			},
			"hidden": 1
		},
		{
			"fieldname": "show_opening_entries",
			"label": __("Show Opening Entries"),
			"fieldtype": "Check",
			"hidden": 1
		},
		{
			"fieldname": "include_default_book_entries",
			"label": __("Include Default Book Entries"),
			"fieldtype": "Check",
			"default": 1,
			"hidden": 1
		},
		{
			"fieldname": "show_cancelled_entries",
			"label": __("Show Cancelled Entries"),
			"fieldtype": "Check",
			"hidden": 1
		}
	],
	onload: function(query_report) {
		query_report.page.clear_menu();
		query_report.page.add_menu_item(__("PDF"), () => {
			const filters = JSON.stringify(query_report.get_values());
			print_settings = {'orientation': 'Portrait'};
			frappe.call({
				method: "essdee.essdee.report.party_ledger.party_ledger.get_ledger_print_html",
				args: {ledger_filters: filters},
				callback: function(r) {
					if(r.message) {
						frappe.render_pdf(r.message, print_settings);
					}
				}
			}
		);
	}
		)
}
};
