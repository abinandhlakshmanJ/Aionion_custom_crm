import frappe


def sync_lead_owner(doc, method):
    """
    Task 4 — PRD Section 6.4
    Before every save, sync lead_owner (Frappe's internal ownership field)
    to the Service RM's user_id if assigned, else fall back to Sales RM's user_id.

    WHY before_save and not after_save:
    - before_save fires before the DB write, so the value is persisted in the
      same transaction — no second save needed, no risk of a stale read.

    WHY frappe.db.get_value and NOT frappe.get_cached_doc:
    - We only need one scalar field (user_id). get_cached_doc loads the entire
      Employee document — wasteful for a single field fetch.
    """
    user_id = None

    if doc.custom_service_rm:
        user_id = frappe.db.get_value("Employee", doc.custom_service_rm, "user_id")

    if not user_id and doc.custom_sales_rm:
        user_id = frappe.db.get_value("Employee", doc.custom_sales_rm, "user_id")

    if user_id:
        doc.lead_owner = user_id


def set_business_type(doc, method):
    """
    Task 1 — PRD Section 4.1
    Auto-set business_type based on product selection.
    - Insurance Sales  → New Business
    - Insurance Renewals → Renewal
    Read-only on the form; enforced server-side here so it cannot be tampered with.
    """
    product_map = {
        "Insurance Sales": "New Business",
        "Insurance Renewals": "Renewal",
    }
    if doc.custom_product in product_map:
        doc.custom_business_type = product_map[doc.custom_product]


def set_sales_rm_defaults(doc, method):
    """
    Task 3 — PRD Section 4.4
    On new lead creation, auto-set Sales RM to the current user's Employee record.
    Only runs when the field is empty (i.e. on first creation, not on every save).

    WHY frappe.db.get_value with filters dict:
    - We need the Employee linked to the current user_id. Single field, one query.
    - No N+1 risk — runs once per save.
    """
    if not doc.custom_sales_rm:
        employee = frappe.db.get_value(
            "Employee",
            {"user_id": frappe.session.user},
            "name"
        )
        if employee:
            doc.custom_sales_rm = employee
