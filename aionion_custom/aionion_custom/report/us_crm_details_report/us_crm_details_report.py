import frappe
from frappe.query_builder import DocType


def execute(filters=None):
    filters = filters or {}
    return get_columns(), get_data(filters)


def get_columns():
    return [
        {"label": "Record", "fieldname": "name", "fieldtype": "Link", "options": "US Subscription Record", "width": 120},
        {"label": "Data Entry Date", "fieldname": "data_entry_date", "fieldtype": "Datetime", "width": 160},
        {"label": "Client Name", "fieldname": "client_name", "fieldtype": "Data", "width": 160},
        {"label": "Email Address", "fieldname": "email_address", "fieldtype": "Data", "width": 180},
        {"label": "Alternate Email", "fieldname": "alternate_email_id", "fieldtype": "Data", "width": 180},
        {"label": "Phone Number", "fieldname": "phone_number", "fieldtype": "Data", "width": 150},
        {"label": "Alternative Phone", "fieldname": "alternative_phone", "fieldtype": "Data", "width": 130},
        {"label": "Country of Residence", "fieldname": "country_of_residence", "fieldtype": "Link", "options": "Country", "width": 150},
        {"label": "Mode of Payment", "fieldname": "mode_of_payment_new", "fieldtype": "Data", "width": 130},
        {"label": "Payment Date", "fieldname": "payment_date", "fieldtype": "Date", "width": 110},
        {"label": "Payment Month", "fieldname": "payment_month", "fieldtype": "Data", "width": 130},
        {"label": "Subscription Type", "fieldname": "subscription_type_new", "fieldtype": "Data", "width": 130},
        {"label": "Client Status", "fieldname": "client_status_new", "fieldtype": "Data", "width": 110},
        {"label": "Quantity", "fieldname": "quantity_new", "fieldtype": "Data", "width": 80},
        {"label": "Currency", "fieldname": "currency_new", "fieldtype": "Data", "width": 80},
        {"label": "Amount Paid", "fieldname": "amount_paid_us_subs", "fieldtype": "Float", "width": 120},
        {"label": "Sub Start Month", "fieldname": "sub_start_month", "fieldtype": "Data", "width": 130},
        {"label": "Sub End Month", "fieldname": "sub_end_month", "fieldtype": "Data", "width": 130},
        {"label": "Sub Start Date", "fieldname": "sub_start_date", "fieldtype": "Date", "width": 110},
        {"label": "Sub End Date", "fieldname": "sub_end_date", "fieldtype": "Date", "width": 110},
        {"label": "Old Sub Month", "fieldname": "old_subscription_month", "fieldtype": "Data", "width": 130},
        {"label": "Sales Done By", "fieldname": "sales_done_by", "fieldtype": "Link", "options": "Employee", "width": 130},
        {"label": "Service RM", "fieldname": "service_rm_name", "fieldtype": "Data", "width": 130},
        {"label": "Lead Source", "fieldname": "lead_source", "fieldtype": "Data", "width": 120},
        {"label": "Team", "fieldname": "team", "fieldtype": "Data", "width": 100},
        {"label": "Old RM", "fieldname": "old_rm", "fieldtype": "Data", "width": 120},
        {"label": "Acknowledgment Sent", "fieldname": "email_sent", "fieldtype": "Data", "width": 140},
        {"label": "Aionion Client Code", "fieldname": "aionion_client_code", "fieldtype": "Data", "width": 130},
        {"label": "Employment Status", "fieldname": "employment_status", "fieldtype": "Data", "width": 130},
    ]


def get_data(filters):
    USRec = DocType("US Subscription Record")
    CRMLead = DocType("CRM Lead")

    query = (
        frappe.qb.from_(USRec)
        .left_join(CRMLead).on(USRec.lead == CRMLead.name)
        .select(
            USRec.name, USRec.data_entry_date, USRec.client_name,
            USRec.email_address, USRec.alternate_email_id,
            USRec.contact_number, USRec.alternative_phone,
            USRec.country_of_residence, USRec.mode_of_payment_new,
            USRec.payment_date, USRec.payment_month,
            USRec.subscription_type_new, USRec.client_status_new,
            USRec.quantity_new, USRec.currency_new, USRec.amount_paid_us_subs,
            USRec.sub_start_month, USRec.sub_end_month,
            USRec.sub_start_date, USRec.sub_end_date,
            USRec.old_subscription_month, USRec.sales_done_by,
            USRec.team, USRec.old_rm, USRec.email_sent,
            USRec.aionion_client_code, USRec.employment_status,
            CRMLead.custom_service_rm_name.as_("service_rm_name"),
            CRMLead.source.as_("lead_source"),
        )
        .where(USRec.docstatus < 2)
    )

    if filters.get("from_date"):
        query = query.where(USRec.data_entry_date >= filters["from_date"])
    if filters.get("to_date"):
        query = query.where(USRec.data_entry_date <= filters["to_date"] + " 23:59:59")
    if filters.get("payment_from_date"):
        query = query.where(USRec.payment_date >= filters["payment_from_date"])
    if filters.get("payment_to_date"):
        query = query.where(USRec.payment_date <= filters["payment_to_date"])
    if filters.get("client_status_new"):
        query = query.where(USRec.client_status_new == filters["client_status_new"])
    if filters.get("subscription_type_new"):
        query = query.where(USRec.subscription_type_new == filters["subscription_type_new"])
    if filters.get("sales_done_by"):
        query = query.where(USRec.sales_done_by == filters["sales_done_by"])
    if filters.get("team"):
        query = query.where(USRec.team == filters["team"])
    if filters.get("mode_of_payment_new"):
        query = query.where(USRec.mode_of_payment_new == filters["mode_of_payment_new"])
    if filters.get("currency_new"):
        query = query.where(USRec.currency_new == filters["currency_new"])
    if filters.get("country_of_residence"):
        query = query.where(USRec.country_of_residence == filters["country_of_residence"])
    if filters.get("lead_source"):
        query = query.where(CRMLead.source == filters["lead_source"])
    if filters.get("email_sent"):
        query = query.where(USRec.email_sent == filters["email_sent"])

    data = query.run(as_dict=True)

    # Concatenate country code + contact number
    for row in data:
        phone = (row.get("contact_number") or "").strip()
        row["phone_number"] = phone

    return data