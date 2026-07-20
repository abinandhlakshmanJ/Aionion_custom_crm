import frappe
def execute():
    # Delete all saved View Settings for Leads
    frappe.db.delete("CRM View Settings", {"crm_doctype": "CRM Lead"})
    frappe.db.commit()
    print("Successfully reset CRM Lead filters!")
