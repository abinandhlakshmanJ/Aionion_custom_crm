import random

import frappe
from frappe.utils.data import cint


def suggest_employee(lead_doc):
    rules = frappe.get_all(
        "Lead Assignment Rule",
        filters={"enabled": 1},
        fields=["name", "condition", "pool", "strategy", "last_assigned_to"],
        order_by="priority asc",
        limit=0,
    )

    for rule in rules:
        if not _matches(rule.condition, lead_doc):
            continue

        members = _eligible_members(rule.pool)
        if not members:
            continue

        chosen = _pick(rule, members)
        if not chosen:
            continue

        frappe.db.set_value(
            "Lead Assignment Rule",
            rule.name,
            "last_assigned_to",
            chosen,
            update_modified=False,
        )

        employee_name = frappe.db.get_value("Employee", chosen, "employee_name")
        return {
            "service_rm": chosen,
            "service_rm_name": employee_name,
            "reason": "Rule: " + rule.name + " (" + rule.strategy + ")",
        }

    frappe.log_error(
        "No Lead Assignment Rule matched (or pool exhausted) for lead " + str(getattr(lead_doc, "name", "<unknown>")),
        "Lead Assignment Engine - No Match",
    )
    return {
        "service_rm": None,
        "reason": "No matching rule or pool exhausted - check Lead Assignment Rule configuration",
    }


def _matches(condition, lead_doc):
    if not condition:
        return True
    return bool(frappe.safe_eval(condition, None, {
        "doc": lead_doc,
        "get_pool_employees": _get_pool_employees,
    }))


def _get_pool_employees(pool_name):
    # Lets a Rule condition check pool MEMBERSHIP (e.g. "is this lead's
    # creator part of Capital Team A pool?") rather than only checking
    # the lead's own fields. Used for team-to-team routing where the
    # match is based on who created the lead, not what the lead is about.
    members = frappe.get_all(
        "Lead Assignment Pool Member",
        filters={"parent": pool_name, "enabled": 1},
        fields=["employee"],
        limit=0,
    )
    return [m.employee for m in members]


def _eligible_members(pool_name):
    members = frappe.get_all(
        "Lead Assignment Pool Member",
        filters={"parent": pool_name, "enabled": 1},
        fields=["employee", "weight", "max_open_leads"],
        order_by="idx asc",
        limit=0,
    )
    eligible = []
    for member in members:
        cap = cint(member.max_open_leads)
        if cap and _open_load(member.employee) >= cap:
            continue
        eligible.append(member)
    return eligible


def _open_load(employee):
    return frappe.db.count(
        "CRM Lead",
        {"custom_service_rm": employee, "docstatus": 0},
    )


def _pick(rule, members):
    strategy = rule.strategy

    if strategy == "Fixed":
        return members[0].employee

    if strategy == "Load Balanced":
        return min(members, key=lambda m: _open_load(m.employee)).employee

    if strategy == "Weighted":
        return _pick_weighted(members)

    employees = [m.employee for m in members]
    if rule.last_assigned_to in employees:
        start = (employees.index(rule.last_assigned_to) + 1) % len(employees)
    else:
        start = 0
    return employees[start]


def _pick_weighted(members):
    import random
    total = sum(m.weight for m in members)
    if total <= 0:
        return random.choice(members).employee

    draw = random.uniform(0, total)
    running_total = 0
    for member in members:
        running_total += member.weight
        if draw <= running_total:
            return member.employee
    return members[-1].employee
