import frappe
def execute():
    # Clear settings for CRM Lead
    frappe.db.delete("CRM View Settings", {"dt": "CRM Lead"})
    frappe.db.commit()
    print("Filters Cleared successfully!")
