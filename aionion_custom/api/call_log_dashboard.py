import frappe
from frappe.query_builder import DocType
from frappe.query_builder.functions import Count, Sum, Coalesce  # ← added Coalesce


@frappe.whitelist()
def get_call_log_summary(from_date=None, to_date=None):
    CRMCallLog = DocType("CRM Call Log")
    current_user = frappe.session.user

    # Roles that can see ALL calls
    manager_roles = {"Administrator", "Sales Manager", "CRM Manager", "System Manager"}
    user_roles = set(frappe.get_roles(current_user))
    is_manager = bool(user_roles & manager_roles) or current_user == "Administrator"

    def base_query():
        q = (
            frappe.qb.from_(CRMCallLog)
            .where(CRMCallLog.reference_doctype == "CRM Lead")
        )
        if from_date:
            q = q.where(CRMCallLog.creation >= from_date)
        if to_date:
            q = q.where(CRMCallLog.creation <= to_date + " 23:59:59")

        # Agents only see their own calls
        if not is_manager:
            q = q.where(
                (CRMCallLog.caller == current_user) | (CRMCallLog.receiver == current_user)
            )
        return q

    my_calls = (
        base_query()
        .select(CRMCallLog.status, Count("*").as_("count"))
        .where(
            (CRMCallLog.caller == current_user) | (CRMCallLog.receiver == current_user)
        )
        .groupby(CRMCallLog.status)
    ).run(as_dict=True)

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
    }@frappe.whitelist()
def get_calls_per_employee(from_date=None, to_date=None):
    """
    Returns per-employee call counts using COALESCE(caller, receiver)
    so both incoming (receiver) and outgoing (caller) calls are captured.
    """
    CRMCallLog = DocType("CRM Call Log")
    Employee = DocType("Employee")

    agent_field = Coalesce(CRMCallLog.caller, CRMCallLog.receiver)

    query = (
        frappe.qb.from_(CRMCallLog)
        .inner_join(Employee)
        .on(Employee.user_id == agent_field)
        .select(
            agent_field.as_("user_id"),
            Employee.name.as_("employee"),
            Employee.employee_name,
            Employee.designation,
            Employee.reports_to,
            Employee.image,
            CRMCallLog.type,
            Count("*").as_("count"),
        )
    )

    if from_date:
        query = query.where(CRMCallLog.start_time >= from_date)
    if to_date:
        query = query.where(CRMCallLog.start_time <= to_date + " 23:59:59")

    rows = query.groupby(agent_field, CRMCallLog.type).run(as_dict=True)

    employees = {}
    for row in rows:
        uid = row.user_id
        if uid not in employees:
            employees[uid] = {
                "user_id": uid,
                "employee": row.employee,
                "employee_name": row.employee_name,
                "designation": row.designation,
                "reports_to": row.reports_to,
                "image": row.image,
                "incoming": 0,
                "outgoing": 0,
                "total": 0,
            }
        count = row.count or 0
        if (row.type or "").lower() == "incoming":
            employees[uid]["incoming"] += count
        elif (row.type or "").lower() == "outgoing":
            employees[uid]["outgoing"] += count
        employees[uid]["total"] += count

    return list(employees.values())


@frappe.whitelist()
def get_hrms_hierarchy():
    """
    Returns active employee list with reports_to for building org tree.
    """
    Employee = DocType("Employee")

    employees = (
        frappe.qb.from_(Employee)
        .select(
            Employee.name,
            Employee.employee_name,
            Employee.reports_to,
            Employee.designation,
            Employee.department,
            Employee.user_id,
            Employee.image,
        )
        .where(Employee.status == "Active")
        .run(as_dict=True)
    )

    return employees