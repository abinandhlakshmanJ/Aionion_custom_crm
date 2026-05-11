import frappe
from frappe.query_builder import DocType

def execute(filters=None):
    filters = filters or {}
    return get_columns(), get_data(filters)

def get_columns():
    return [
        {"label": "Data Entry Date", "fieldname": "data_entry_date", "fieldtype": "Date", "width": 120},
        {"label": "Email Address", "fieldname": "email_address", "fieldtype": "Data", "width": 180},
        {"label": "EMP Code", "fieldname": "emp_code", "fieldtype": "Data", "width": 100},
        {"label": "EMP Name", "fieldname": "emp_name", "fieldtype": "Data", "width": 140},
        {"label": "EMP Team", "fieldname": "emp_team", "fieldtype": "Data", "width": 100},
        {"label": "EMP Branch", "fieldname": "emp_branch", "fieldtype": "Data", "width": 120},
        {"label": "Aionion Client Code", "fieldname": "aionion_client_code", "fieldtype": "Data", "width": 140},
        {"label": "Client Name", "fieldname": "client_name", "fieldtype": "Data", "width": 160},
        {"label": "Contact Number", "fieldname": "contact_number", "fieldtype": "Data", "width": 130},
        {"label": "Client Email ID", "fieldname": "client_email", "fieldtype": "Data", "width": 180},
        {"label": "Intended Investment", "fieldname": "intended_investment", "fieldtype": "Data", "width": 150},
        {"label": "Indian Investments", "fieldname": "indian_investments", "fieldtype": "Data", "width": 180},
        {"label": "Country of Residence", "fieldname": "country_of_residence", "fieldtype": "Link", "options": "Country", "width": 150},
        {"label": "Employment Status", "fieldname": "employment_status", "fieldtype": "Data", "width": 130},
        {"label": "Month", "fieldname": "month", "fieldtype": "Data", "width": 120},
        {"label": "Year", "fieldname": "year", "fieldtype": "Data", "width": 80},
        {"label": "Assigned By", "fieldname": "assigned_by", "fieldtype": "Link", "options": "Employee", "width": 130},
        {"label": "Eligibility", "fieldname": "eligibility", "fieldtype": "Data", "width": 120},
        {"label": "Status", "fieldname": "us_status", "fieldtype": "Data", "width": 120},
        {"label": "Progress", "fieldname": "progress", "fieldtype": "Data", "width": 150},
        {"label": "Detailed Remarks", "fieldname": "detailed_remarks", "fieldtype": "Data", "width": 200},
        {"label": "Reminder Date", "fieldname": "reminder_date", "fieldtype": "Date", "width": 120},
        {"label": "Alternative Phone", "fieldname": "alternative_phone", "fieldtype": "Data", "width": 130},
        {"label": "Current Country", "fieldname": "current_country", "fieldtype": "Link", "options": "Country", "width": 130},
        {"label": "Alternative Email", "fieldname": "alternative_email", "fieldtype": "Data", "width": 180},
        {"label": "Alternate Email ID", "fieldname": "alternate_email_id", "fieldtype": "Data", "width": 180},
        {"label": "EMP Phone No", "fieldname": "emp_phone", "fieldtype": "Data", "width": 130},
    ]

def get_data(filters):
    USRec = DocType("US Subscription Record")
    query = (
        frappe.qb.from_(USRec)
        .select(
            USRec.data_entry_date, USRec.email_address, USRec.emp_code,
            USRec.emp_name, USRec.emp_team, USRec.emp_branch,
            USRec.aionion_client_code, USRec.client_name, USRec.contact_number,
            USRec.client_email, USRec.intended_investment, USRec.indian_investments,
            USRec.country_of_residence, USRec.employment_status, USRec.month,
            USRec.year, USRec.assigned_by, USRec.eligibility, USRec.us_status,
            USRec.progress, USRec.detailed_remarks, USRec.reminder_date,
            USRec.alternative_phone, USRec.current_country, USRec.alternative_email,
            USRec.alternate_email_id, USRec.emp_phone,
        )
        .where(USRec.docstatus < 2)
    )
    if filters.get("emp_team"):
        query = query.where(USRec.emp_team == filters["emp_team"])
    if filters.get("eligibility"):
        query = query.where(USRec.eligibility == filters["eligibility"])
    if filters.get("us_status"):
        query = query.where(USRec.us_status == filters["us_status"])
    if filters.get("from_date"):
        query = query.where(USRec.data_entry_date >= filters["from_date"])
    if filters.get("to_date"):
        query = query.where(USRec.data_entry_date <= filters["to_date"])
    if filters.get("month"):
        query = query.where(USRec.month == filters["month"])
    return query.run(as_dict=True)
