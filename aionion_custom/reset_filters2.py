import frappe
def execute():
    frappe.db.delete("CRM View Settings", {"doctype_name": "CRM Lead"})
    frappe.db.commit()
    print("Done")
