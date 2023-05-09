// Copyright (c) 2020, Aerele Technologies Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on('Essdee Application Settings', {
	// refresh: function(frm) {

	// }
	sync_customers_now: function() {
		frappe.call({
			method: "essdee.essdee.doctype.essdee_application_settings.essdee_application_settings.sync_data",
			freeze: true,
			callback: function(r) {
				frappe.msgprint(__("Sync data sent to partner site."))
			}
		})
	}
});
