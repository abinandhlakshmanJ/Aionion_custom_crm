import frappe
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