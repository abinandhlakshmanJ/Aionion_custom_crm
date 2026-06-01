import frappe
from frappe import _
from frappe.utils import today


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data    = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("Employee"),        "fieldname": "employee_name",   "fieldtype": "Data", "width": 260},
        {"label": _("Designation"),     "fieldname": "designation",     "fieldtype": "Data", "width": 160},
        {"label": _("Reports To"),      "fieldname": "reports_to_name", "fieldtype": "Data", "width": 180},
        {"label": _("Own Leads"),       "fieldname": "own_leads",       "fieldtype": "Int",  "width": 110},
        {"label": _("Team Total Leads"),"fieldname": "team_leads",      "fieldtype": "Int",  "width": 150},
    ]


def get_data(filters):

    from_date = filters.get("from_date") or frappe.utils.get_first_day(today()).strftime("%Y-%m-%d")
    to_date   = filters.get("to_date")   or today()
    from_dt   = f"{from_date} 00:00:00"
    to_dt     = f"{to_date} 23:59:59"

    # ── Step 1: Fetch ALL active employees ────────────────────────────────────
    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "user_id", "reports_to", "designation"],
        limit=0,    # fetch all, not just first 20
    )

    emp_map = {e.name: e for e in employees}

    for e in employees:
        rt = e.get("reports_to")
        e["reports_to_name"] = emp_map[rt].employee_name if (rt and rt in emp_map) else None

    # ── Step 2: Fetch ALL CRM Leads ───────────────────────────────────────────
    lead_filters = [["creation", "between", [from_dt, to_dt]]]
    if filters.get("entity"):
        lead_filters.append(["custom_entity", "=", filters.get("entity")])
    if filters.get("lead_status"):
        lead_filters.append(["status", "=", filters.get("lead_status")])

    leads = frappe.get_all(
        "CRM Lead",
        filters=lead_filters,
        fields=["owner"],
        limit=0,    # 7000+ leads — must fetch all
    )

    # Build user_email → lead count map
    # owner = Frappe system field (email) — matches exactly what users see in list view
    lead_count_map = {}
    for lead in leads:
        if lead.owner:
            lead_count_map[lead.owner] = lead_count_map.get(lead.owner, 0) + 1

    # ── Step 3: Build children map ────────────────────────────────────────────
    children_map = {}
    for e in employees:
        parent = e.reports_to if (e.reports_to and e.reports_to in emp_map) else None
        children_map.setdefault(parent, []).append(e)

    # ── Step 4: Visibility — scope to current user's subtree ─────────────────
    current_user = frappe.session.user
    user_roles   = frappe.get_roles(current_user)
    is_admin     = "System Manager" in user_roles or current_user == "Administrator"

    if is_admin:
        roots = children_map.get(None, [])
    else:
        my_emp_code = frappe.db.get_value(
            "Employee", {"user_id": current_user, "status": "Active"}, "name"
        )
        if my_emp_code and my_emp_code in emp_map:
            roots = [emp_map[my_emp_code]]
        else:
            return []

    # ── Step 5: Recursive descendant helper ───────────────────────────────────
    def get_all_descendants(emp_id):
        result = []
        for child in children_map.get(emp_id, []):
            result.append(child.name)
            result.extend(get_all_descendants(child.name))
        return result

    # ── Step 6: Build rows ────────────────────────────────────────────────────
    rows = []

    def build_rows(emp, level=0):
        descendants    = get_all_descendants(emp.name)
        all_member_ids = [emp.name] + descendants

        # Join via user_id (email) — same key as owner field in CRM Lead
        team_leads = sum(
            lead_count_map.get(emp_map.get(m, {}).get("user_id") or "", 0)
            for m in all_member_ids
        )

        # Own leads — this employee's email matches CRM Lead.owner
        own_leads = lead_count_map.get(emp.user_id or "", 0)

        rows.append(frappe._dict({
            "employee_name":   emp.employee_name,
            "designation":     emp.designation     or "—",
            "reports_to_name": emp.reports_to_name or "—",
            "own_leads":       own_leads,
            "team_leads":      team_leads,
            "indent":          level,
        }))

        for child in children_map.get(emp.name, []):
            build_rows(child, level + 1)

    for root in roots:
        build_rows(root, level=0)

    return rows