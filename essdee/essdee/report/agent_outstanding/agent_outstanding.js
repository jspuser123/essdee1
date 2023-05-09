// Copyright (c) 2016, Aerele Technologies Pvt Ltd and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Agent Outstanding"] = {
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
			"fieldname":"customer_group",
			"label": __("Customer Group"),
			"fieldtype": "Link",
			"options": "Customer Group",
			get_data: function(txt) {
				return frappe.db.get_link_options('Customer Group', txt);
			},
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
	],
	onload: function(query_report) {
		query_report.page.clear_menu();
		query_report.page.add_menu_item(__("PDF"), () => {
			const filters = JSON.stringify(query_report.get_values());
			const query_string = frappe.utils.get_query_string(frappe.get_route_str());
			const query_params = frappe.utils.get_query_params(query_string);
			print_settings = {'orientation': 'Landscape'};
			frappe.call({
				method: "essdee.essdee.report.agent_outstanding.agent_outstanding.get_agent_outstanding_print_html",
				freeze: true,
				args: {outstanding_filters: filters, prepared_report_name: query_params.prepared_report_name},
				callback: function(r) {
					if(r.message) {
						frappe.render_pdf(r.message, print_settings);
					}
				}
			}
		);
	}
		),
		query_report.page.add_menu_item(__("Send This Report To Telegram"), () => {
			const filters = JSON.stringify(query_report.get_values());
			const query_string = frappe.utils.get_query_string(frappe.get_route_str());
			const query_params = frappe.utils.get_query_params(query_string);
			frappe.call({
				method: "essdee.essdee.report.agent_late_payment.agent_late_payment.background_enqueue_send_reports",
				freeze: true,
				args: {action:'send_single_report', filters: filters, prepared_report_name: query_params.prepared_report_name, report_name: 'Agent Outstanding'}
			}
		);
	}
		),
		query_report.page.add_menu_item(__("Send All Reports To Telegram"), () => {
			const filters = JSON.stringify(query_report.get_values());
			frappe.call({
				method: "essdee.essdee.report.agent_late_payment.agent_late_payment.background_enqueue_send_reports",
				freeze: true,
				args: {action:'send_all_reports', filters: filters, report_name: 'Agent Outstanding'}
			}
		);
	}
		)
}
};
