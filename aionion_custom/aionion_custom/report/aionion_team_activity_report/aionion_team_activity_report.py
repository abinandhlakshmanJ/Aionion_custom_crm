import frappe
from frappe import _
from frappe.utils import today


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("Employee"), "fieldname": "employee_name", "fieldtype": "Data", "width": 220},
        {"label": _("Designation"), "fieldname": "designation", "fieldtype": "Data", "width": 150},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Data", "width": 160},
        {"label": _("Team Strength"), "fieldname": "team_strength", "fieldtype": "Int", "width": 120},
        {"label": _("Team Logged In"), "fieldname": "logged_in_count", "fieldtype": "Int", "width": 120},
        {"label": _("Not Logged In"), "fieldname": "not_logged_in_count", "fieldtype": "Int", "width": 120},
        {"label": _("Own Leads Today"), "fieldname": "own_leads_today", "fieldtype": "Int", "width": 130},
        {"label": _("Team Leads Today"), "fieldname": "team_leads_today", "fieldtype": "Int", "width": 140},
        {"label": _("Own Total Leads"), "fieldname": "own_total_leads", "fieldtype": "Int", "width": 130},
        {"label": _("Team Total Leads"), "fieldname": "team_total_leads", "fieldtype": "Int", "width": 140},
        {"label": _("Own Emails Today"), "fieldname": "own_emails_today", "fieldtype": "Int", "width": 130},
        {"label": _("Team Emails Today"), "fieldname": "team_emails_today", "fieldtype": "Int", "width": 140},
        {"label": _("Own Calls Today"), "fieldname": "own_calls_today", "fieldtype": "Int", "width": 130},
        {"label": _("Team Calls Today"), "fieldname": "team_calls_today", "fieldtype": "Int", "width": 140},
    ]


def get_data(filters):
    from_date = filters.get("from_date") or today()
    to_date = filters.get("to_date") or today()
    from_dt = f"{from_date} 00:00:00"
    to_dt = f"{to_date} 23:59:59"

    # Step 1: All active employees
    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "user_id", "reports_to", "designation", "department"],
        limit=0,
    )
    emp_map = {e.name: e for e in employees}
    emp_code_to_uid = {e.name: e.user_id for e in employees if e.user_id}

    # Step 2: Logged in users in date range
    logs = frappe.get_all(
        "Activity Log",
        filters={
            "operation": "Login",
            "status": "Success",
            "communication_date": ["between", [from_dt, to_dt]],
        },
        fields=["user"],
        limit=0,
    )
    logged_in_users = set(l.user for l in logs)

    # Step 3: Leads today - union of lead_owner and custom_sales_rm
    leads_today_raw = frappe.get_all(
        "CRM Lead",
        filters=[["creation", ">=", from_dt], ["creation", "<=", to_dt]],
        fields=["name", "lead_owner", "custom_sales_rm"],
        limit=0,
    )
    leads_today_map = {}
    for l in leads_today_raw:
        matched_uids = set()
        if l.lead_owner:
            matched_uids.add(l.lead_owner)
        if l.custom_sales_rm and l.custom_sales_rm in emp_code_to_uid:
            matched_uids.add(emp_code_to_uid[l.custom_sales_rm])
        for uid in matched_uids:
            leads_today_map[uid] = leads_today_map.get(uid, 0) + 1

    # Step 4: Total leads all time - union of lead_owner and custom_sales_rm
    leads_total_raw = frappe.get_all(
        "CRM Lead",
        fields=["name", "lead_owner", "custom_sales_rm"],
        limit=0,
    )
    leads_total_map = {}
    for l in leads_total_raw:
        matched_uids = set()
        if l.lead_owner:
            matched_uids.add(l.lead_owner)
        if l.custom_sales_rm and l.custom_sales_rm in emp_code_to_uid:
            matched_uids.add(emp_code_to_uid[l.custom_sales_rm])
        for uid in matched_uids:
            leads_total_map[uid] = leads_total_map.get(uid, 0) + 1

    # Step 5: Emails sent in date range
    emails_today = frappe.get_all(
        "Communication",
        filters=[
            ["sent_or_received", "=", "Sent"],
            ["reference_doctype", "=", "CRM Lead"],
            ["creation", ">=", from_dt],
            ["creation", "<=", to_dt],
        ],
        fields=["sender"],
        limit=0,
    )
    emails_today_map = {}
    for e in emails_today:
        o = e.sender or ""
        emails_today_map[o] = emails_today_map.get(o, 0) + 1

    # Step 6: Calls in date range
    calls_outgoing = frappe.get_all(
        "CRM Call Log",
        filters=[
            ["type", "=", "Outgoing"],
            ["caller", "!=", ""],
            ["creation", ">=", from_dt],
            ["creation", "<=", to_dt],
        ],
        fields=["caller"],
        limit=0,
    )
    calls_incoming = frappe.get_all(
        "CRM Call Log",
        filters=[
            ["type", "=", "Incoming"],
            ["receiver", "!=", ""],
            ["creation", ">=", from_dt],
            ["creation", "<=", to_dt],
        ],
        fields=["receiver"],
        limit=0,
    )
    calls_today_map = {}
    for c in calls_outgoing:
        o = c.caller or ""
        if o:
            calls_today_map[o] = calls_today_map.get(o, 0) + 1
    for c in calls_incoming:
        o = c.receiver or ""
        if o:
            calls_today_map[o] = calls_today_map.get(o, 0) + 1

    # Step 7: Children map
    children_map = {}
    for e in employees:
        parent = e.reports_to if (e.reports_to and e.reports_to in emp_map) else None
        children_map.setdefault(parent, []).append(e)

    # Step 8: Visibility
    current_user = frappe.session.user
    user_roles = frappe.get_roles(current_user)
    is_admin = "System Manager" in user_roles or current_user == "Administrator"

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

    # Step 9: Recursive descendant helper
    def get_all_descendants(emp_id):
        result = []
        for child in children_map.get(emp_id, []):
            result.append(child.name)
            result.extend(get_all_descendants(child.name))
        return result

    # Step 10: Build rows
    rows = []

    def build_rows(emp, level=0):
        descendants = get_all_descendants(emp.name)
        all_member_ids = [emp.name] + descendants

        member_user_ids = [
            emp_map[m].user_id
            for m in all_member_ids
            if emp_map.get(m) and emp_map[m].user_id
        ]

        uid = emp.user_id or ""

        # Login
        logged_in_count = sum(1 for u in member_user_ids if u in logged_in_users)
        not_logged_in_count = len(member_user_ids) - logged_in_count

        # Leads - own vs team (union logic applied)
        own_leads_today = leads_today_map.get(uid, 0)
        team_leads_today = sum(leads_today_map.get(u, 0) for u in member_user_ids)
        own_total_leads = leads_total_map.get(uid, 0)
        team_total_leads = sum(leads_total_map.get(u, 0) for u in member_user_ids)

        # Emails
        own_emails_today = emails_today_map.get(uid, 0)
        team_emails_today = sum(emails_today_map.get(u, 0) for u in member_user_ids)

        # Calls
        own_calls_today = calls_today_map.get(uid, 0)
        team_calls_today = sum(calls_today_map.get(u, 0) for u in member_user_ids)

        rows.append(frappe._dict({
            "employee_name": emp.employee_name,
            "designation": emp.designation or "",
            "department": emp.department or "",
            "team_strength": len(all_member_ids),
            "logged_in_count": logged_in_count,
            "not_logged_in_count": not_logged_in_count,
            "own_leads_today": own_leads_today,
            "team_leads_today": team_leads_today,
            "own_total_leads": own_total_leads,
            "team_total_leads": team_total_leads,
            "own_emails_today": own_emails_today,
            "team_emails_today": team_emails_today,
            "own_calls_today": own_calls_today,
            "team_calls_today": team_calls_today,
            "indent": level,
        }))

        for child in children_map.get(emp.name, []):
            build_rows(child, level + 1)

    for root in roots:
        build_rows(root, level=0)

    return rows
