import frappe
def execute():
    # Let's print all view settings
    views = frappe.db.get_all("CRM View Settings", fields=["name", "dt"])
    print(views)
