import frappe
from frappe.query_builder import DocType

def execute(filters=None):
    filters = filters or {}
    return get_columns(), get_data(filters)

def get_columns():
    return [
        {"label": "Record", "fieldname": "name", "fieldtype": "Link", "options": "US Subscription Record", "width": 120},
        {"label": "Client Name", "fieldname": "client_name", "fieldtype": "Data", "width": 160},
        {"label": "New Email ID", "fieldname": "email_address", "fieldtype": "Data", "width": 180},
        {"label": "Old Email ID", "fieldname": "alternate_email_id", "fieldtype": "Data", "width": 180},
        {"label": "Country Code", "fieldname": "country_code", "fieldtype": "Data", "width": 100},
        {"label": "Contact Number", "fieldname": "contact_number", "fieldtype": "Data", "width": 130},
        {"label": "Alternative Phone", "fieldname": "alternative_phone", "fieldtype": "Data", "width": 130},
        {"label": "Country of Residence", "fieldname": "country_of_residence", "fieldtype": "Link", "options": "Country", "width": 150},
        {"label": "Mode of Payment", "fieldname": "mode_of_payment_new", "fieldtype": "Data", "width": 130},
        {"label": "Payment Date", "fieldname": "payment_date", "fieldtype": "Date", "width": 110},
        {"label": "Payment Month", "fieldname": "payment_month", "fieldtype": "Data", "width": 130},
        {"label": "Subscription Type", "fieldname": "subscription_type_new", "fieldtype": "Data", "width": 130},
        {"label": "Client Status", "fieldname": "client_status_new", "fieldtype": "Data", "width": 110},
        {"label": "Second Client Status", "fieldname": "second_client_status", "fieldtype": "Data", "width": 140},
        {"label": "Quantity", "fieldname": "quantity_new", "fieldtype": "Data", "width": 80},
        {"label": "Currency", "fieldname": "currency_new", "fieldtype": "Data", "width": 80},
        {"label": "Amount Paid", "fieldname": "amount_paid_us_subs", "fieldtype": "Currency", "width": 120},
        {"label": "Sub Start Month", "fieldname": "sub_start_month", "fieldtype": "Data", "width": 130},
        {"label": "Sub End Month", "fieldname": "sub_end_month", "fieldtype": "Data", "width": 130},
        {"label": "Sub Start Date", "fieldname": "sub_start_date", "fieldtype": "Date", "width": 110},
        {"label": "Sub End Date", "fieldname": "sub_end_date", "fieldtype": "Date", "width": 110},
        {"label": "Old Sub End Month", "fieldname": "old_subscription_end_month", "fieldtype": "Data", "width": 140},
        {"label": "Old Sub Month", "fieldname": "old_subscription_month", "fieldtype": "Data", "width": 130},
        {"label": "Lead Source", "fieldname": "lead_source", "fieldtype": "Data", "width": 120},
        {"label": "Sales Done By", "fieldname": "sales_done_by", "fieldtype": "Link", "options": "Employee", "width": 130},
        {"label": "Service RM", "fieldname": "service_rm", "fieldtype": "Link", "options": "Employee", "width": 130},
        {"label": "Old RM", "fieldname": "old_rm", "fieldtype": "Data", "width": 120},
        {"label": "Team", "fieldname": "team", "fieldtype": "Data", "width": 100},
        {"label": "Email Sent", "fieldname": "email_sent", "fieldtype": "Data", "width": 100},
        {"label": "Risk Declaration", "fieldname": "risk_declaration", "fieldtype": "Data", "width": 130},
        {"label": "Payment Status", "fieldname": "payment_status", "fieldtype": "Data", "width": 120},
    ]

def get_data(filters):
    USRec = DocType("US Subscription Record")
    query = (
        frappe.qb.from_(USRec)
        .select(
            USRec.name, USRec.client_name, USRec.email_address, USRec.alternate_email_id,
            USRec.country_code, USRec.contact_number, USRec.alternative_phone,
            USRec.country_of_residence, USRec.mode_of_payment_new, USRec.payment_date,
            USRec.payment_month, USRec.subscription_type_new, USRec.client_status_new,
            USRec.second_client_status, USRec.quantity_new, USRec.currency_new,
            USRec.amount_paid_us_subs, USRec.sub_start_month, USRec.sub_end_month,
            USRec.sub_start_date, USRec.sub_end_date, USRec.old_subscription_end_month,
            USRec.old_subscription_month, USRec.lead_source, USRec.sales_done_by,
            USRec.service_rm, USRec.old_rm, USRec.team, USRec.email_sent,
            USRec.risk_declaration, USRec.payment_status,
        )
        .where(USRec.docstatus < 2)
    )
    if filters.get("payment_status"):
        query = query.where(USRec.payment_status == filters["payment_status"])
    if filters.get("client_status_new"):
        query = query.where(USRec.client_status_new == filters["client_status_new"])
    if filters.get("subscription_type_new"):
        query = query.where(USRec.subscription_type_new == filters["subscription_type_new"])
    if filters.get("from_date"):
        query = query.where(USRec.payment_date >= filters["from_date"])
    if filters.get("to_date"):
        query = query.where(USRec.payment_date <= filters["to_date"])
    if filters.get("team"):
        query = query.where(USRec.team == filters["team"])
    return query.run(as_dict=True)
