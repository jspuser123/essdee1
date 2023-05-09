// Copyright (c) 2021, Aerele Technologies Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on('SD TDS Percentage Settings', {
	onload: function(frm) {
		frm.set_query("account_head", "tds_mapping", function() {
			return {
				filters: {
					"root_type":"Expense",
					"is_group": 0
				}
			};
		});
	},
	fetch_all_expense_head: function(frm) {
		const set_fields = ['account_head', 'tds_for_firm', 'tds_for_individual'];
		frappe.call({
			method: "essdee.essdee.doctype.sd_tds_percentage_settings.sd_tds_percentage_settings.fetch_all_expense_head",
			freeze: true,
			freeze_message: __("Fetching Accounts..."),
			args: {
				tds_mapping: frm.doc.tds_mapping
			},
			callback: function(r) {
				if (r.message) {
					frm.set_value('tds_mapping', []);
					$.each(r.message, function(i, d) {
						var row = frm.add_child('tds_mapping');
						for (let key in d) {
							if (in_list(set_fields, key)) {
								row[key] = d[key];
							}
						}
					});
				}
			}
		});
		frm.refresh_field("tds_mapping");
		frm.refresh_fields();
	}
});
