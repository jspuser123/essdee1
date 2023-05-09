frappe.ui.form.on("Customer", {
    refresh : (frm) => {
        if(!frm.doc.__islocal) {
        frm.add_custom_button(__("Sync With Partner"), function() {
            frm.trigger('sync_with_partner');
        });
    }
    },
    sync_with_partner: function(frm){
        frappe.call({
			method: "essdee.essdee.doctype.essdee_application_settings.essdee_application_settings.sync_with_partner",
			freeze: true,
            args: {customer: frm.doc.name},
        }
        )
    }
});