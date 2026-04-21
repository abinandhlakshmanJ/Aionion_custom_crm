import frappe
from frappe import _


@frappe.whitelist()
def create_cross_sell_lead(customer_name, entity, product):
    """
    PRD Section 9.4
    Manual cross-sell lead creation from Customer record.
    Pre-fills customer details into the new lead.
    """
    customer = frappe.get_doc("Customer", customer_name)

    # Map business type
    business_type_map = {
        "Insurance Sales": "New Business",
        "Insurance Renewals": "Renewal",
    }

    # Parse first/last name
    parts = (customer.customer_name or "").split(" ", 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ""

    lead = frappe.get_doc({
        "doctype": "CRM Lead",
        "first_name": first_name,
        "last_name": last_name,
        "lead_name": customer.customer_name,
        "mobile_no": customer.custom_mobile,
        "email": customer.custom_email,
        "custom_entity": entity,
        "custom_product": product,
        "custom_business_type": business_type_map.get(product, "New Business"),
        "custom_customer": customer_name,
        "custom_dob": customer.custom_dob,
        "custom_residency": customer.custom_residency,
        "custom_client_category": "Aionion Client",
        "lead_owner": frappe.session.user,
        "status": "New",
    })
    lead.insert(ignore_permissions=True)
    frappe.db.commit()

    return lead.name


@frappe.whitelist()
def get_customer_products(customer_name):
    """
    PRD Section 10 — Assigned Products panel
    Returns all products this customer holds across all entities.
    """
    products = []

    # Insurance Records
    insurance_records = frappe.get_all("Insurance Record",
        filters={"customer": customer_name},
        fields=["name", "insurance_products", "policy_status",
                "policy_number", "policy_expiry_date", "custom_mis_status"])
    for r in insurance_records:
        products.append({
            "type": "Insurance",
            "record": r.name,
            "product": r.insurance_products,
            "status": r.policy_status,
            "reference": r.policy_number,
            "expiry": str(r.policy_expiry_date or ""),
            "mis_status": r.custom_mis_status
        })

    # Bonds Records
    bonds_records = frappe.get_all("Bonds Purchase Record",
        filters={"customer": customer_name},
        fields=["name", "docstatus"])
    for r in bonds_records:
        products.append({
            "type": "Bonds",
            "record": r.name,
            "product": "Bonds",
            "status": "Active" if r.docstatus == 1 else "Draft",
        })

    # Mutual Funds Records
    mf_records = frappe.get_all("Mutual Funds Record",
        filters={"customer": customer_name},
        fields=["name", "docstatus"])
    for r in mf_records:
        products.append({
            "type": "Mutual Funds",
            "record": r.name,
            "product": "Mutual Funds",
            "status": "Active" if r.docstatus == 1 else "Draft",
        })

    # US Subscription Records
    us_records = frappe.get_all("US Subscription Record",
        filters={"customer": customer_name},
        fields=["name", "docstatus"])
    for r in us_records:
        products.append({
            "type": "US Subscription",
            "record": r.name,
            "product": "US Subscription",
            "status": "Active" if r.docstatus == 1 else "Draft",
        })

    return products
