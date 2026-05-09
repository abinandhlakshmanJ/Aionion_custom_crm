import frappe
from frappe.query_builder import DocType
from frappe.query_builder.functions import Count, Sum


@frappe.whitelist()
def get_call_log_summary(from_date=None, to_date=None):
	"""
	Returns total, incoming, outgoing, missed call counts
	and average duration for the given date range.
	"""
	CRMCallLog = DocType("CRM Call Log")

	query = (
		frappe.qb.from_(CRMCallLog)
		.select(
			CRMCallLog.type,
			CRMCallLog.status,
			Count("*").as_("count"),
		)
	)

	if from_date:
		query = query.where(CRMCallLog.start_time >= from_date)
	if to_date:
		query = query.where(CRMCallLog.start_time <= to_date + " 23:59:59")

	rows = query.groupby(CRMCallLog.type, CRMCallLog.status).run(as_dict=True)

	summary = {
		"total": 0,
		"incoming": 0,
		"outgoing": 0,
		"missed": 0,
		"completed": 0,
	}

	for row in rows:
		call_type = (row.type or "").lower()
		call_status = (row.status or "").lower()
		count = row.count or 0

		summary["total"] += count

		if call_type == "incoming":
			summary["incoming"] += count
		elif call_type == "outgoing":
			summary["outgoing"] += count

		if call_status in ("missed", "no answer"):
			summary["missed"] += count
		elif call_status in ("completed", "answered"):
			summary["completed"] += count

	return summary


@frappe.whitelist()
def get_calls_per_employee(from_date=None, to_date=None):
	"""
	Returns per-employee call counts (incoming + outgoing)
	joined with HRMS Employee for hierarchy data.
	"""
	CRMCallLog = DocType("CRM Call Log")
	Employee = DocType("Employee")

	query = (
		frappe.qb.from_(CRMCallLog)
		.inner_join(Employee)
		.on(Employee.user_id == CRMCallLog.caller)
		.select(
			CRMCallLog.caller.as_("user_id"),
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

	rows = query.groupby(CRMCallLog.caller, CRMCallLog.type).run(as_dict=True)

	# Aggregate into per-employee dict
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
		call_type = (row.type or "").lower()

		if call_type == "incoming":
			employees[uid]["incoming"] += count
		elif call_type == "outgoing":
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
