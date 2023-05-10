import frappe
from frappe.contacts.doctype.address.address import get_address_display

@frappe.whitelist()
def sd_print_address(id):
    doc = frappe.get_doc('Journal Entry', id)
    for x in doc.accounts:
        if x:
            party_type=x.party_type
            party=x.party
            if party_type == "Supplier":
                primary_address=frappe.db.get_value("Supplier",party,'supplier_primary_address') 
                address_display = get_address_display(primary_address)
            elif party_type == "Customer":
                primary_address=frappe.db.get_value("Customer",party,'customer_primary_address') 
                address_display = get_address_display(primary_address)

    return address_display