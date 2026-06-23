import frappe

_ADMIN_ROLES = {"System Manager", "Administrator"}


def get_customer_permission_query(user=None):
    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return ""

    user_roles = set(frappe.get_roles(user))
    if user_roles & _ADMIN_ROLES:
        return ""

    rm_code = frappe.db.get_value(
        "Employee",
        filters={"user_id": user, "status": "Active"},
        fieldname="name",
    )

    if not rm_code:
        return "1=0"

    safe_rm_code = frappe.db.escape(rm_code)
    return f"`tabCustomer`.`custom_rm_code` = {safe_rm_code}"


def force_disable_user_permission(doc, method):
    if doc.create_user_permission:
        doc.create_user_permission = 0
