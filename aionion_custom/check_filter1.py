import frappe

def execute():
    # Inspect all records in CRM View Settings
    docs = frappe.db.get_all("CRM View Settings", fields=["*"])
    print("=== CRM VIEW SETTINGS ===")
    for d in docs:
        print(d)

    # Inspect all records in CRM Lead
    leads = frappe.db.get_all("CRM Lead", fields=["*"])
    print("=== CRM LEADS ===")
    for l in leads:
        print(l)
