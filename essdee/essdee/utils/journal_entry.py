import frappe
from frappe.contacts.doctype.address.address import get_address_display

@frappe.whitelist()
def sd_print_address(id):
    doc = frappe.get_doc('Journal Entry', id)
    if doc.accounts[0].party_type == "Supplier" or doc.accounts[1].party_type == "Supplier":
        sub=frappe.db.get_value("Supplier",(doc.accounts[0].party or doc.accounts[1].party),'supplier_primary_address') 
        address_display = get_address_display(sub)
    elif doc.accounts[0].party_type == "Customer" or doc.accounts[1].party_type == "Customer":
        sub=frappe.db.get_value("Customer",(doc.accounts[0].party or doc.accounts[1].party),'customer_primary_address') 
        address_display = get_address_display(sub)
    else:
        address_display = 'Supplier or Customer address is None'

    return address_display