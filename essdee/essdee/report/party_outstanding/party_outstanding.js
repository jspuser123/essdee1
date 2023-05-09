// Copyright (c) 2016, Aerele Technologies Pvt Ltd and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Party Outstanding"] = {
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
			"fieldname":"report_date",
			"label": __("Posting Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname":"ageing_based_on",
			"label": __("Ageing Based On"),
			"fieldtype": "Select",
			"options": 'Posting Date\nDue Date',
			"default": "Posting Date"
		},
		{
			"fieldname":"range1",
			"label": __("Ageing Range 1"),
			"fieldtype": "Int",
			"default": 30,
			"reqd": 1,
			"hidden": 1
		},
		{
			"fieldname":"range2",
			"label": __("Ageing Range 2"),
			"fieldtype": "Int",
			"default": 60,
			"reqd": 1,
			"hidden": 1
		},
		{
			"fieldname":"range3",
			"label": __("Ageing Range 3"),
			"fieldtype": "Int",
			"default": 90,
			"reqd": 1,
			"hidden": 1
		},
		{
			"fieldname":"range4",
			"label": __("Ageing Range 4"),
			"fieldtype": "Int",
			"default": 120,
			"reqd": 1,
			"hidden": 1
		},
		{
			"fieldname":"finance_book",
			"label": __("Finance Book"),
			"fieldtype": "Link",
			"options": "Finance Book",
			"hidden": 1
		},
		{
			"fieldname":"cost_center",
			"label": __("Cost Center"),
			"fieldtype": "Link",
			"options": "Cost Center",
			get_query: () => {
				var company = frappe.query_report.get_filter_value('company');
				return {
					filters: {
						'company': company
					}
				}
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
			"fieldname":"period",
			"label": __("Period(No.of.months)"),
			"fieldtype": "Int",
			"default": 14
		},
		{
			"fieldname":"customer_group",
			"label": __("Customer Group"),
			"fieldtype": "Link",
			"options": "Customer Group",
			"hidden": 1
		},
		{
			"fieldname":"payment_terms_template",
			"label": __("Payment Terms Template"),
			"fieldtype": "Link",
			"options": "Payment Terms Template",
			"hidden": 1
		},
		{
			"fieldname":"territory",
			"label": __("Territory"),
			"fieldtype": "Link",
			"options": "Territory",
			"hidden": 1
		},
		{
			"fieldname":"sales_partner",
			"label": __("Sales Partner"),
			"fieldtype": "Link",
			"options": "Sales Partner",
			"hidden": 1
		},
		{
			"fieldname":"sales_person",
			"label": __("Sales Person"),
			"fieldtype": "Link",
			"options": "Sales Person",
			"hidden": 1
		},
		{
			"fieldname": "group_by_party",
			"label": __("Group By Customer"),
			"fieldtype": "Check",
			"hidden": 1
		},
		{
			"fieldname":"based_on_payment_terms",
			"label": __("Based On Payment Terms"),
			"fieldtype": "Check",
			"hidden": 1
		},
		{
			"fieldname":"show_future_payments",
			"label": __("Show Future Payments"),
			"fieldtype": "Check",
			"hidden": 1
		},
		{
			"fieldname":"show_delivery_notes",
			"label": __("Show Linked Delivery Notes"),
			"fieldtype": "Check",
			"hidden": 1
		},
		{
			"fieldname":"show_sales_person",
			"label": __("Show Sales Person"),
			"fieldtype": "Check",
			"hidden": 1
		},
		{
			"fieldname":"tax_id",
			"label": __("Tax Id"),
			"fieldtype": "Data",
			"hidden": 1
		},
		{
			"fieldname":"customer_name",
			"label": __("Customer Name"),
			"fieldtype": "Data",
			"hidden": 1
		},
		{
			"fieldname":"payment_terms",
			"label": __("Payment Tems"),
			"fieldtype": "Data",
			"hidden": 1
		},
		{
			"fieldname":"credit_limit",
			"label": __("Credit Limit"),
			"fieldtype": "Currency",
			"hidden": 1
		}
	],
	onload: function(query_report) {
		query_report.page.clear_menu();
		query_report.page.add_menu_item(__("PDF"), () => {
			const filters = JSON.stringify(query_report.get_values());
			print_settings = {'orientation': 'Portrait'};
			frappe.call({
				method: "essdee.essdee.report.party_outstanding.party_outstanding.get_outstanding_print_html",
				args: {outstanding_filters: filters},
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
