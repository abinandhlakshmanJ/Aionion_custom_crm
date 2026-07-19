import frappe

def execute():
    emp = frappe.db.get_value("Employee", {}, "name")
    if not emp:
        comp = frappe.db.get_value("Company", {}, "name")
        if not comp:
            comp_doc = frappe.get_doc({
                "doctype": "Company",
                "company_name": "Aionion Capital",
                "default_currency": "INR",
                "country": "India"
            })
            comp_doc.insert(ignore_permissions=True)
            comp = comp_doc.name

        emp_doc = frappe.get_doc({
            "doctype": "Employee",
            "first_name": "abinandh",
            "user_id": "Administrator",
            "gender": "Male",
            "date_of_birth": "1995-01-01",
            "date_of_joining": "2024-01-01",
            "company": comp,
            "status": "Active"
        })
        emp_doc.insert(ignore_permissions=True)
        emp = emp_doc.name

    lead = frappe.get_doc({
        "doctype": "CRM Lead",
        "first_name": "Acme",
        "last_name": "Corporation",
        "email": "contact@acme.com",
        "mobile_no": "+1-555-0199",
        "status": "New",
        "converted": 0,
        "lead_owner": "Administrator",
        "owner": "Administrator",
        "custom_product": "Insurance Sales",
        "custom_entity": "Aionion Insurance",
        "custom_business_type": "New Business",
        "custom_client_category": "Aionion Client",
        "custom_residency": "Indian",
        "custom_sales_rm": emp,
    })
    lead.insert(ignore_permissions=True)
    frappe.db.commit()
    print(f"Successfully created Lead: {lead.name} ({lead.first_name} {lead.last_name}) assigned to Administrator")
