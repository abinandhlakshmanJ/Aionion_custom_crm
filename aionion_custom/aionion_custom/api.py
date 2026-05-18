import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Count


def get_team_user_ids(current_user):
    """
    BFS down the reports_to tree from current_user's employee record.
    Returns list of all user_ids the current_user can see (self + all subordinates).
    """
    my_employees = frappe.get_all(
        "Employee",
        filters={"user_id": current_user, "status": "Active"},
        fields=["name"]
    )
    if not my_employees:
        return [current_user]

    visited_emp_ids = set(e.name for e in my_employees)
    queue = list(visited_emp_ids)

    while queue:
        batch  = queue[:50]
        queue  = queue[50:]
        subordinates = frappe.get_all(
            "Employee",
            filters={"reports_to": ["in", batch], "status": "Active"},
            fields=["name"]
        )
        for sub in subordinates:
            if sub.name not in visited_emp_ids:
                visited_emp_ids.add(sub.name)
                queue.append(sub.name)

    # Resolve employee IDs → user_ids
    emp_users = frappe.get_all(
        "Employee",
        filters={"name": ["in", list(visited_emp_ids)]},
        fields=["user_id"]
    )
    user_ids = list({e.user_id for e in emp_users if e.user_id})

    if current_user not in user_ids:
        user_ids.append(current_user)

    return user_ids


@frappe.whitelist()
def get_call_log_summary(from_date=None, to_date=None):
    CRMCallLog   = DocType("CRM Call Log")
    current_user = frappe.session.user
    is_admin     = current_user == "Administrator"

    # Get the users this person can see based on hierarchy
    team_users = None if is_admin else get_team_user_ids(current_user)

    def base_query():
        q = (
            frappe.qb.from_(CRMCallLog)
            .where(CRMCallLog.reference_doctype == "CRM Lead")
        )
        if from_date:
            q = q.where(CRMCallLog.creation >= from_date)
        if to_date:
            q = q.where(CRMCallLog.creation <= to_date + " 23:59:59")

        # Scope to hierarchy — skip filter for Administrator
        if not is_admin and team_users:
            q = q.where(
                (CRMCallLog.caller.isin(team_users)) |
                (CRMCallLog.receiver.isin(team_users))
            )
        return q

    # My Calls — always just current user
    my_calls = (
        base_query()
        .select(CRMCallLog.status, Count("*").as_("count"))
        .where(
            (CRMCallLog.caller == current_user) | (CRMCallLog.receiver == current_user)
        )
        .groupby(CRMCallLog.status)
    ).run(as_dict=True)

    # Team breakdown — scoped by hierarchy
    caller_rows = (
        base_query()
        .select(CRMCallLog.caller.as_("agent"), Count("*").as_("total_calls"))
        .where(CRMCallLog.caller.isnotnull())
        .groupby(CRMCallLog.caller)
    ).run(as_dict=True)

    receiver_rows = (
        base_query()
        .select(CRMCallLog.receiver.as_("agent"), Count("*").as_("total_calls"))
        .where(CRMCallLog.receiver.isnotnull())
        .groupby(CRMCallLog.receiver)
    ).run(as_dict=True)

    agent_totals = {}
    for r in caller_rows + receiver_rows:
        agent = r.get("agent")
        if agent:
            agent_totals[agent] = agent_totals.get(agent, 0) + r["total_calls"]

    agents = list(agent_totals.keys())
    if not agents:
        return {
            "my_summary": {"user": current_user, "total": 0, "by_status": []},
            "team_summary": [], "managers": [], "team_leads": []
        }

    user_map = {
        u["name"]: u for u in frappe.get_all(
            "User", filters={"name": ["in", agents]}, fields=["name", "full_name"]
        )
    }

    HasRole = DocType("Has Role")
    role_map = {}
    for r in (
        frappe.qb.from_(HasRole)
        .select(HasRole.parent, HasRole.role)
        .where(
            (HasRole.parent.isin(agents)) &
            (HasRole.role.isin(["CRM Manager", "CRM TL", "Sales Team Lead", "Sales Manager"]))
        )
        .run(as_dict=True)
    ):
        role_map.setdefault(r["parent"], []).append(r["role"])

    enriched_team = sorted([
        {
            "user": agent,
            "full_name": user_map.get(agent, {}).get("full_name", agent),
            "total_calls": agent_totals[agent],
            "roles": role_map.get(agent, ["Agent"]),
            "is_me": agent == current_user
        }
        for agent in agents
    ], key=lambda x: x["total_calls"], reverse=True)

    return {
        "my_summary": {
            "user": current_user,
            "total": sum(r["count"] for r in my_calls),
            "by_status": my_calls
        },
        "team_summary": enriched_team,
        "managers": [r for r in enriched_team if any("Manager" in x for x in r["roles"])],
        "team_leads": [r for r in enriched_team if any("TL" in x or "Lead" in x for x in r["roles"])]
    }


@frappe.whitelist()
def get_email_summary(from_date=None, to_date=None):
    Comm = DocType("Communication")
    current_user = frappe.session.user

    def apply_filters(q):
        q = q.where(
            (Comm.communication_medium == "Email") &
            (Comm.reference_doctype == "CRM Lead") &
            (Comm.sent_or_received == "Sent")
        )
        if from_date:
            q = q.where(Comm.communication_date >= from_date)
        if to_date:
            q = q.where(Comm.communication_date <= to_date)
        return q

    my_emails = apply_filters(
        frappe.qb.from_(Comm)
        .select(Comm.status, Count("*").as_("count"))
        .where(Comm.owner == current_user)
        .groupby(Comm.status)
    ).run(as_dict=True)

    team_emails = apply_filters(
        frappe.qb.from_(Comm)
        .select(Comm.owner, Count("*").as_("total_sent"))
        .groupby(Comm.owner)
        .orderby(Count("*"), order=frappe.qb.desc)
    ).run(as_dict=True)

    owners = [r["owner"] for r in team_emails]
    if not owners:
        return {
            "my_summary": {"user": current_user, "total_sent": 0, "by_status": []},
            "team_summary": [], "managers": [], "team_leads": []
        }

    user_map = {
        u["name"]: u for u in frappe.get_all(
            "User", filters={"name": ["in", owners]}, fields=["name", "full_name"]
        )
    }

    HasRole = DocType("Has Role")
    role_map = {}
    for r in (
        frappe.qb.from_(HasRole)
        .select(HasRole.parent, HasRole.role)
        .where(
            (HasRole.parent.isin(owners)) &
            (HasRole.role.isin(["CRM Manager", "CRM TL", "Sales Team Lead", "Sales Manager"]))
        )
        .run(as_dict=True)
    ):
        role_map.setdefault(r["parent"], []).append(r["role"])

    enriched_team = [
        {
            "user": row["owner"],
            "full_name": user_map.get(row["owner"], {}).get("full_name", row["owner"]),
            "total_sent": row["total_sent"],
            "roles": role_map.get(row["owner"], ["Agent"]),
            "is_me": row["owner"] == current_user
        }
        for row in team_emails
    ]

    return {
        "my_summary": {
            "user": current_user,
            "total_sent": sum(r["count"] for r in my_emails),
            "by_status": my_emails
        },
        "team_summary": enriched_team,
        "managers": [r for r in enriched_team if any("Manager" in x for x in r["roles"])],
        "team_leads": [r for r in enriched_team if any("TL" in x or "Lead" in x for x in r["roles"])]
    }


# ── CRM IO — Import / Export ──────────────────────────────────────────────────

@frappe.whitelist()
def run_lead_us_import(file_url):
    """
    Called from crm-io page.
    Accepts a Frappe File URL, resolves the path, runs import_records.
    """
    file_doc = frappe.db.get_value("File", {"file_url": file_url}, ["file_url", "is_private"], as_dict=True)
    if not file_doc:
        frappe.throw(_("File not found: {0}").format(file_url))

    site_path = frappe.utils.get_site_path()
    if file_url.startswith("/private/"):
        file_path = site_path + file_url
    else:
        file_path = frappe.utils.get_site_path("public") + file_url

    from aionion_custom.scripts.import_lead_us_subscription import import_records
    results = import_records(file_path)
    return results


@frappe.whitelist()
def run_lead_us_export():
    """
    Called from crm-io page.
    Exports all CRM Leads + US Subscription Records to a CSV and returns download URL.
    """
    from aionion_custom.scripts.export_lead_us_subscription import export

    file_name = "lead_us_export.csv"
    file_path = frappe.utils.get_site_path("private", "files", file_name)

    export(file_path)

    existing = frappe.db.get_value("File", {"file_name": file_name, "is_private": 1}, "name")
    if existing:
        frappe.delete_doc("File", existing, ignore_permissions=True)

    with open(file_path, "rb") as f:
        content = f.read()

    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": file_name,
        "is_private": 1,
        "content": content,
    })
    file_doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {"file_url": file_doc.file_url, "file_name": file_name}


@frappe.whitelist()
def download_import_template():
    """
    Returns a blank CSV template with all lead__ and us__ headers.
    """
    from aionion_custom.scripts.export_lead_us_subscription import LEAD_FIELDS, US_FIELDS
    import csv, io

    fieldnames = [f"lead__{f}" for f in LEAD_FIELDS] + [f"us__{f}" for f in US_FIELDS]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerow({f: "" for f in fieldnames})

    content = output.getvalue().encode("utf-8")
    file_name = "lead_us_import_template.csv"

    existing = frappe.db.get_value("File", {"file_name": file_name, "is_private": 1}, "name")
    if existing:
        frappe.delete_doc("File", existing, ignore_permissions=True)

    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": file_name,
        "is_private": 1,
        "content": content,
    })
    file_doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {"file_url": file_doc.file_url, "file_name": file_name}


@frappe.whitelist()
def preview_import_file(file_url):
    """
    Returns first 5 rows of the uploaded CSV for preview before import.
    """
    import csv

    site_path = frappe.utils.get_site_path()
    if file_url.startswith("/private/"):
        file_path = site_path + file_url
    else:
        file_path = frappe.utils.get_site_path("public") + file_url

    rows = []
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        for i, row in enumerate(reader):
            if i >= 5:
                break
            rows.append(dict(row))

    return {"headers": headers, "rows": rows}