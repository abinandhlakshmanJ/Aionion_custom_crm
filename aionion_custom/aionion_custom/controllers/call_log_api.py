import frappe

@frappe.whitelist()
def get_call_log_summary(from_date=None, to_date=None):
    conditions = []
    params = {}
    if from_date:
        conditions.append('DATE(creation) >= %(from_date)s')
        params['from_date'] = from_date
    if to_date:
        conditions.append('DATE(creation) <= %(to_date)s')
        params['to_date'] = to_date
    where = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''
    sql = ('SELECT COUNT(*) as total,'
           ' COALESCE(SUM(type="Incoming"),0) as incoming,'
           ' COALESCE(SUM(type="Outgoing"),0) as outgoing,'
           ' COALESCE(SUM(status="Missed"),0) as missed,'
           ' ROUND(COALESCE(AVG(duration),0),1) as avg_duration'
           ' FROM `tabCRM Call Log` ') + where
    result = frappe.db.sql(sql, params, as_dict=True)
    return result[0] if result else {}


@frappe.whitelist()
def get_calls_per_employee(from_date=None, to_date=None, search=None, limit=20, offset=0):
    date_filter = ''
    params = {}
    if from_date:
        date_filter += ' AND DATE(cl.creation) >= %(from_date)s'
        params['from_date'] = from_date
    if to_date:
        date_filter += ' AND DATE(cl.creation) <= %(to_date)s'
        params['to_date'] = to_date
    search_filter = ''
    if search:
        search_filter = ' AND e.employee_name LIKE %(search)s'
        params['search'] = '%' + search + '%'
    params['limit'] = int(limit)
    params['offset'] = int(offset)
    sql = ('SELECT e.employee_name, e.designation, e.reports_to, e.name as employee_id,'
           ' u.name as user_email, COALESCE(SUM(cl.type="Incoming"),0) as incoming,'
           ' COALESCE(SUM(cl.type="Outgoing"),0) as outgoing,'
           ' COALESCE(SUM(cl.status="Missed"),0) as missed,'
           ' COUNT(cl.name) as total'
           ' FROM `tabEmployee` e'
           ' LEFT JOIN `tabUser` u ON u.name = e.user_id'
           ' LEFT JOIN `tabCRM Call Log` cl ON cl.owner = u.name') + date_filter
    sql += ' WHERE e.status = "Active"' + search_filter
    sql += ' GROUP BY e.name ORDER BY total DESC LIMIT %(limit)s OFFSET %(offset)s'
    data = frappe.db.sql(sql, params, as_dict=True)
    for row in data:
        if row.get('reports_to'):
            manager = frappe.db.get_value('Employee', row['reports_to'], 'employee_name')
            row['reports_to_name'] = manager or row['reports_to']
        else:
            row['reports_to_name'] = '-'
    return data


@frappe.whitelist()
def get_employee_call_detail(user_email, from_date=None, to_date=None):
    params = {"email": user_email}
    date_filter = ""
    if from_date:
        date_filter += " AND DATE(cl.creation) >= %(from_date)s"
        params["from_date"] = from_date
    if to_date:
        date_filter += " AND DATE(cl.creation) <= %(to_date)s"
        params["to_date"] = to_date

    return frappe.db.sql(
        "SELECT cl.name, cl.type, cl.status, cl.duration, cl.from_, cl.to,"
        " cl.creation, l.name as lead_name, l.lead_name as lead_full_name"
        " FROM `tabCRM Call Log` cl"
        " LEFT JOIN `tabCRM Lead` l ON l.mobile_no = cl.from_ OR l.mobile_no = cl.to"
        " WHERE cl.owner = %(email)s" + date_filter +
        " ORDER BY cl.creation DESC LIMIT 50",
        params, as_dict=True
    )
