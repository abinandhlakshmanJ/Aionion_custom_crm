import frappe
def execute():
    # Clear User Document Preference for CRM Lead
    frappe.db.delete("User Document Preference", {"document": "CRM Lead"})
    frappe.db.commit()
    print("User Document Preferences Cleared successfully!")
