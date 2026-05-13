import frappe
from frappe.query_builder import DocType
from frappe.query_builder.functions import Count


@frappe.whitelist()
def get_call_log_summary(from_date=None, to_date=None):
    CRMCallLog = DocType("CRM Call Log")
    current_user = frappe.session.user

    def apply_filters(q):
        if from_date:
            q = q.where(CRMCallLog.creation >= from_date)
        if to_date:
            q = q.where(CRMCallLog.creation <= to_date)
        return q

    my_calls = apply_filters(
        frappe.qb.from_(CRMCallLog)
        .select(CRMCallLog.status, Count("*").as_("count"))
        .where(CRMCallLog.owner == current_user)
        .groupby(CRMCallLog.status)
    ).run(as_dict=True)

    team_calls = apply_filters(
        frappe.qb.from_(CRMCallLog)
        .select(CRMCallLog.owner, Count("*").as_("total_calls"))
        .groupby(CRMCallLog.owner)
        .orderby(Count("*"), order=frappe.qb.desc)
    ).run(as_dict=True)

    owners = [r["owner"] for r in team_calls]
    if not owners:
        return {
            "my_summary": {"user": current_user, "total": 0, "by_status": []},
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
            "total_calls": row["total_calls"],
            "roles": role_map.get(row["owner"], ["Agent"]),
            "is_me": row["owner"] == current_user
        }
        for row in team_calls
    ]

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
