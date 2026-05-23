import frappe
from frappe import _
from frappe.utils import today


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data = get_data(filters)
    return columns, data


# ─────────────────────────────────────────────────────────────────────────────
# COLUMNS
# ─────────────────────────────────────────────────────────────────────────────

def get_columns():
    return [
        {
            "label": _("Employee"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 260,
        },
        {
            "label": _("Designation"),
            "fieldname": "designation",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": _("Reports To"),
            "fieldname": "reports_to_name",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": _("Team Strength"),
            "fieldname": "team_strength",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": _("Logged In"),
            "fieldname": "logged_in_count",
            "fieldtype": "Data",
            "width": 110,
        },
        {
            "label": _("Not Logged In"),
            "fieldname": "not_logged_in_count",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": _("My Login Status"),
            "fieldname": "login_status",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("First Login"),
            "fieldname": "first_login",
            "fieldtype": "Datetime",
            "width": 170,
        },
        {
            "label": _("Last Logout"),
            "fieldname": "last_logout",
            "fieldtype": "Datetime",
            "width": 170,
        },
    ]


# ─────────────────────────────────────────────────────────────────────────────
# FILTERS (defined here for reference — set these in the JSON or via UI)
# ─────────────────────────────────────────────────────────────────────────────
#
#   from_date         DateField   (default: today)
#   to_date           DateField   (default: today)
#   company           Link → Company
#   top_level_manager Link → Employee  (optional: scope to one manager's tree)
#


# ─────────────────────────────────────────────────────────────────────────────
# MAIN DATA FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def get_data(filters):
    from_date = filters.get("from_date") or today()
    to_date   = filters.get("to_date")   or today()

    from_dt = f"{from_date} 00:00:00"
    to_dt   = f"{to_date} 23:59:59"

    # ── Step 1: Fetch all active employees ───────────────────────────────────
    emp_filters = {"status": "Active"}
    if filters.get("company"):
        emp_filters["company"] = filters.get("company")

    employees = frappe.get_all(
        "Employee",
        filters=emp_filters,
        fields=[
            "name",            # employee code  e.g. EMP-0001
            "employee_name",   # human name
            "user_id",         # email — joins to Activity Log
            "reports_to",      # reports_to employee code
            "designation",
            "department",
            "company",
        ],
    )

    # index by employee code
    emp_map = {e.name: e for e in employees}

    # resolve reports_to → name  (single pass, no extra queries)
    for e in employees:
        rt = e.get("reports_to")
        e["reports_to_name"] = emp_map[rt].employee_name if rt and rt in emp_map else None

    # ── Step 2: Fetch Activity Logs for the date range ────────────────────────
    logs = frappe.get_all(
        "Activity Log",
        filters={
            "operation": ["in", ["Login", "Logout"]],
            "status": "Success",
            "communication_date": ["between", [from_dt, to_dt]],
        },
        fields=["user", "operation", "communication_date"],
        order_by="communication_date asc",
    )

    # user_email → { logins: [dt, ...], logouts: [dt, ...] }
    user_logs = {}
    for log in logs:
        u = log.user
        if u not in user_logs:
            user_logs[u] = {"logins": [], "logouts": []}
        if log.operation == "Login":
            user_logs[u]["logins"].append(log.communication_date)
        else:
            user_logs[u]["logouts"].append(log.communication_date)

    # ── Step 3: Build children map ────────────────────────────────────────────
    # None key → top-level employees (no valid reports_to in active emp set)
    children_map = {}
    for e in employees:
        parent = e.reports_to if (e.reports_to and e.reports_to in emp_map) else None
        children_map.setdefault(parent, []).append(e)

    # ── Step 4: Determine root(s) ─────────────────────────────────────────────
    top_mgr = filters.get("top_level_manager")
    if top_mgr and top_mgr in emp_map:
        roots = [emp_map[top_mgr]]
    else:
        roots = children_map.get(None, [])

    # ── Step 5: Recursive helper — all descendant IDs under an employee ───────
    def get_all_descendants(emp_id):
        result = []
        for child in children_map.get(emp_id, []):
            result.append(child.name)
            result.extend(get_all_descendants(child.name))
        return result

    # ── Step 6: Build flat output rows (Frappe uses `indent` for tree display) ─
    rows = []

    def build_rows(emp, level=0):
        descendants   = get_all_descendants(emp.name)
        all_member_ids = [emp.name] + descendants          # self + entire sub-tree

        # Collect all user_ids in this sub-tree
        member_user_ids = [
            emp_map[m].user_id
            for m in all_member_ids
            if emp_map.get(m) and emp_map[m].user_id
        ]

        logged_in_set     = {u for u in member_user_ids if user_logs.get(u, {}).get("logins")}
        not_logged_in_set = set(member_user_ids) - logged_in_set

        team_strength       = len(all_member_ids)
        logged_in_count     = len(logged_in_set)
        not_logged_in_count = len(not_logged_in_set)

        # Personal login/logout for THIS employee
        my_uid    = emp.user_id or ""
        my_logs   = user_logs.get(my_uid, {})
        first_login  = min(my_logs["logins"])  if my_logs.get("logins")  else None
        last_logout  = max(my_logs["logouts"]) if my_logs.get("logouts") else None
        is_logged_in = bool(my_uid and my_uid in logged_in_set)

        has_team = bool(descendants)

        # Team summary label e.g. "10 / 4 logged in"
        team_label      = f"{team_strength}" if has_team else "—"
        logged_label    = f"{logged_in_count} / {team_strength}" if has_team else "—"
        not_logged_label = f"{not_logged_in_count}"              if has_team else "—"

        rows.append(
            frappe._dict({
                "employee_name":      emp.employee_name,
                "designation":        emp.designation or "—",
                "reports_to_name":    emp.reports_to_name or "—",
                "team_strength":      team_label,
                "logged_in_count":    logged_label,
                "not_logged_in_count": not_logged_label,
                "login_status":       "✅ Logged In" if is_logged_in else "❌ Not Logged In",
                "first_login":        first_login,
                "last_logout":        last_logout,
                "indent":             level,          # Frappe uses this for tree indentation
            })
        )

        # Recurse into direct reports
        for child in children_map.get(emp.name, []):
            build_rows(child, level + 1)

    for root in roots:
        build_rows(root, level=0)

    return rows
