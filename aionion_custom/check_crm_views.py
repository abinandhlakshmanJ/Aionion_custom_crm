import frappe

def execute():
    users = frappe.db.get_all("User", fields=["name", "email", "first_name"])
    print("=== USERS ===")
    for u in users:
        print(u)

    # Assign lead_owner to user if needed
    user_name = frappe.db.get_value("User", {"email": ["like", "%abinandh%"]}, "name") or "Administrator"
    frappe.db.set_value("CRM Lead", "CRM-LEAD-2026-00001", "lead_owner", user_name)
    frappe.db.commit()
    print(f"Updated CRM-LEAD-2026-00001 lead_owner to: {user_name}")
