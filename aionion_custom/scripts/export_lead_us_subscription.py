"""
Export script: CRM Lead (US entity) + US Subscription Record
Place at:
  aionion_custom/aionion_custom/scripts/export_lead_us_subscription.py
"""

import csv
import frappe
from frappe.query_builder import DocType

# ── CRM Lead fields to export ──────────────────────────────────────────────
LEAD_FIELDS = [
    "name",
    "first_name",
    "last_name",
    "email",
    "mobile_no",
    "custom_entity",
    "custom_product",
    "custom_lead_date",
    "custom_sales_rm",
    "custom_sales_rm_code",
    "custom_sales_rm_branch",
    "custom_sales_rm_team",
    "custom_service_rm",
    "custom_lead_status_1",
    "custom_lead_status_2",
    "custom_pan_number",
    "custom_dob",
    "custom_aionion_client_code",
    "custom_us_amount",
    "custom_us_quantity",
    "custom_us_subscription_end_date",
    "custom_us_currency",
    "custom_us_mode_of_payment",
    "custom_us_subscription_type",
    "custom_us_payment_date",
    "status",
    "source",
]

# ── US Subscription Record fields to export ────────────────────────────────
US_FIELDS = [
    "name",
    "lead",
    # Lead Generation Sheet columns
    "data_entry_date",
    "email_address",
    "emp_code",
    "emp_name",
    "emp_team",
    "emp_branch",
    "emp_phone",
    "aionion_client_code",
    "client_name",
    "contact_number",
    "client_email",
    "intended_investment",
    "indian_investments",
    "country_of_residence",       # = "Current Country" in sheet
    "employment_status",
    "month",
    "year",
    "assigned_by",
    "eligibility",
    "us_status",
    "progress",
    "detailed_remarks",
    "reminder_date",
    "alternative_phone",
    "alternative_email",
    "alternate_email_id",
    # CRM Details columns
    "new_email_id",
    "old_email_id",
    "country_code",
    "mode_of_payment_new",
    "payment_date",
    "payment_month",
    "subscription_type_new",
    "client_status_new",
    "second_client_status",
    "quantity_new",
    "currency_new",
    "amount_paid_us_subs",
    "sub_start_month",
    "sub_end_month",
    "sub_start_date",
    "sub_end_date",
    "old_subscription_end_month",
    "lead_source",
    "sales_done_by",
    "service_rm",
    "old_rm",
    "team",
    "email_sent",
    "risk_declaration",
    "us_remarks",
    "attended_webinar",
    # RM Details
    "rm_employee_code",
    "rm_employee_name",
    "lead_entry_date",
]

# ── Human-readable header labels for the CSV ──────────────────────────────
# Format: "us__fieldname": "Sheet Column Label"
US_FIELD_LABELS = {
    "us__name":                    "US Record ID",
    "us__lead":                    "CRM Lead ID",
    "us__data_entry_date":         "Time / Data Entry Date",
    "us__email_address":           "Email Address",
    "us__emp_code":                "EMP Code (Sales RM)",
    "us__emp_name":                "EMP Name",
    "us__emp_team":                "EMP Team",
    "us__emp_branch":              "EMP Branch",
    "us__emp_phone":               "EMP Phone No",
    "us__aionion_client_code":     "Aionion Client Code",
    "us__client_name":             "Client Name",
    "us__contact_number":          "Client Contact Number",
    "us__client_email":            "Client Email ID",
    "us__intended_investment":     "Client Intended Investment in US Market",
    "us__indian_investments":      "Client Current Indian Investments",
    "us__country_of_residence":    "Current Country / Country of Residence",
    "us__employment_status":       "Client Employment Status",
    "us__month":                   "Month",
    "us__year":                    "Year",
    "us__assigned_by":             "Assigned To (Service RM)",
    "us__eligibility":             "Eligibility",
    "us__us_status":               "Status",
    "us__progress":                "Progress",
    "us__detailed_remarks":        "Detailed Remarks",
    "us__reminder_date":           "Reminder Date / Postponed Month",
    "us__alternative_phone":       "Alternative Phone Number",
    "us__alternative_email":       "Alternative Email",
    "us__alternate_email_id":      "Alternate Email ID",
    "us__new_email_id":            "New Email ID",
    "us__old_email_id":            "Old Email ID",
    "us__country_code":            "Country Code",
    "us__mode_of_payment_new":     "Mode of Payment",
    "us__payment_date":            "Payment Date",
    "us__payment_month":           "Payment Month",
    "us__subscription_type_new":   "Subscription Type",
    "us__client_status_new":       "Client Status",
    "us__second_client_status":    "Second Client Status",
    "us__quantity_new":            "Quantity",
    "us__currency_new":            "Currency",
    "us__amount_paid_us_subs":     "Amount Paid (US Subs)",
    "us__sub_start_month":         "Subscription Start Month-Year",
    "us__sub_end_month":           "Subscription End Month-Year",
    "us__sub_start_date":          "Subscription Start Date",
    "us__sub_end_date":            "Subscription End Date",
    "us__old_subscription_end_month": "Old Subscription End Month",
    "us__lead_source":             "Lead Source",
    "us__sales_done_by":           "Sales Done By",
    "us__service_rm":              "Service RM",
    "us__old_rm":                  "Old RM",
    "us__team":                    "Team",
    "us__email_sent":              "Acknowledgment Sent",
    "us__risk_declaration":        "Risk Declaration Received",
    "us__us_remarks":              "Remarks",
    "us__attended_webinar":        "Attended Webinar",
    "us__rm_employee_code":        "RM Employee Code",
    "us__rm_employee_name":        "RM Employee Name",
    "us__lead_entry_date":         "Lead Entry Date",
    # Lead fields
    "lead__name":                  "Lead ID",
    "lead__first_name":            "First Name",
    "lead__last_name":             "Last Name",
    "lead__email":                 "Lead Email",
    "lead__mobile_no":             "Mobile No",
    "lead__custom_entity":         "Entity",
    "lead__custom_product":        "Product",
    "lead__custom_lead_date":      "Lead Date",
    "lead__custom_sales_rm":       "Sales RM",
    "lead__custom_sales_rm_code":  "Sales RM Code",
    "lead__custom_sales_rm_branch":"Sales RM Branch",
    "lead__custom_sales_rm_team":  "Sales RM Team",
    "lead__custom_service_rm":     "Service RM (Lead)",
    "lead__custom_lead_status_1":  "Lead Status 1",
    "lead__custom_lead_status_2":  "Lead Status 2",
    "lead__custom_pan_number":     "PAN Number",
    "lead__custom_dob":            "Date of Birth",
    "lead__custom_aionion_client_code": "Aionion Client Code (Lead)",
    "lead__custom_us_amount":      "Amount Paid (Lead)",
    "lead__custom_us_quantity":    "Quantity (Lead)",
    "lead__custom_us_subscription_end_date": "Subscription End Date (Lead)",
    "lead__custom_us_currency":    "Currency (Lead)",
    "lead__custom_us_mode_of_payment": "Mode of Payment (Lead)",
    "lead__custom_us_subscription_type": "Subscription Type (Lead)",
    "lead__custom_us_payment_date":"Payment Date (Lead)",
    "lead__status":                "Lead Status",
    "lead__source":                "Lead Source (Lead)",
}


def export(file_path):
    """
    Exports all Aionion Global CRM Leads joined with their US Subscription Records.
    CSV uses human-readable column headers with fieldname in brackets for import mapping.
    """
    Lead  = DocType("CRM Lead")
    USSub = DocType("US Subscription Record")

    rows = (
        frappe.qb.from_(Lead)
        .left_join(USSub)
        .on(USSub.lead == Lead.name)
        .select(
            *[Lead[f].as_(f"lead__{f}") for f in LEAD_FIELDS],
            *[USSub[f].as_(f"us__{f}") for f in US_FIELDS],
        )
        .where(Lead.custom_entity == "Aionion Global")
        .run(as_dict=True)
    )

    # Build fieldnames in order: lead fields first, then us fields
    fieldnames = [f"lead__{f}" for f in LEAD_FIELDS] + [f"us__{f}" for f in US_FIELDS]

    # Build display headers: "Label [fieldname]" — makes import mapping obvious
    display_headers = [
        f"{US_FIELD_LABELS.get(fn, fn)} [{fn}]"
        for fn in fieldnames
    ]

    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Row 1: display headers (human readable)
        writer.writerow(display_headers)
        # Row 2: raw fieldnames (for import reference)
        writer.writerow(fieldnames)
        # Data rows
        for row in rows:
            writer.writerow([row.get(fn, "") for fn in fieldnames])

    return len(rows)