"""
Import CRM Lead + US Subscription Record from the CSV produced by export_lead_us_subscription.py

Run via bench console:
    from aionion_custom.scripts.import_lead_us_subscription import import_records
    import_records("/home/frappe/frappe-bench/sites/airplane.local/private/files/lead_us_export.csv")
"""

import csv
import frappe
from frappe.utils.data import cstr, cint, flt, getdate, get_datetime


# ──────────────────────────────────────────────
# Field type maps — tells the importer how to cast each value
# ──────────────────────────────────────────────
LEAD_INT_FIELDS = {
    "custom_tenure", "custom_health_members", "custom_term_age",
    "custom_motor_vehicle_year", "custom_travel_duration", "custom_travel_members",
    "custom_bonds_number_of_units", "custom_us_quantity",
}
LEAD_FLOAT_FIELDS = {
    "custom_sum_assured", "custom_gross_premium", "custom_net_premium",
    "custom_bonds_amount", "custom_mf_amount", "custom_us_amount", "annual_revenue",
}
LEAD_DATE_FIELDS = {
    "custom_lead_date", "custom_expiry_date", "custom_mis_verified_date",
    "custom_term_dob", "custom_bonds_execution_date", "custom_equity_activation_date",
    "custom_us_payment_date", "custom_us_subscription_end_date",
    "custom_parent_expiry_date", "custom_dob", "custom_event_date",
    "custom_motor_policy_copy",  # Attach — kept as string, no cast needed; removing from here
}
LEAD_DATE_FIELDS = {
    "custom_lead_date", "custom_expiry_date", "custom_mis_verified_date",
    "custom_term_dob", "custom_bonds_execution_date", "custom_equity_activation_date",
    "custom_us_payment_date", "custom_us_subscription_end_date",
    "custom_parent_expiry_date", "custom_dob", "custom_event_date",
}
LEAD_CHECK_FIELDS = {"custom_is_existing_customer", "converted"}

US_INT_FIELDS = {"quantity"}
US_FLOAT_FIELDS = {"amount_paid_us_subs"}
US_DATE_FIELDS = {
    "subscription_end_date", "reminder_date",
    "sub_start_date", "sub_end_date", "payment_date",
}
US_DATETIME_FIELDS = {"lead_entry_date", "data_entry_date"}


def _cast_lead(fieldname, raw_value):
    """Cast a raw CSV string to the correct Python type for a CRM Lead field."""
    v = cstr(raw_value).strip()
    if not v:
        return None
    if fieldname in LEAD_INT_FIELDS:
        return cint(v) or None
    if fieldname in LEAD_FLOAT_FIELDS:
        return flt(v) or None
    if fieldname in LEAD_DATE_FIELDS:
        try:
            return getdate(v)
        except Exception:
            return None
    if fieldname in LEAD_CHECK_FIELDS:
        return cint(v)
    return v


def _cast_us(fieldname, raw_value):
    """Cast a raw CSV string to the correct Python type for a US Subscription Record field."""
    v = cstr(raw_value).strip()
    if not v:
        return None
    if fieldname in US_INT_FIELDS:
        return cint(v) or None
    if fieldname in US_FLOAT_FIELDS:
        return flt(v) or None
    if fieldname in US_DATE_FIELDS:
        try:
            return getdate(v)
        except Exception:
            return None
    if fieldname in US_DATETIME_FIELDS:
        try:
            return get_datetime(v)
        except Exception:
            return None
    return v


def import_records(file_path):
    """
    Reads the export CSV and upserts CRM Lead + US Subscription Record.
    - CRM Lead is matched by lead__name  (the Frappe document name / ID)
    - US Subscription is matched by us__name, or by us__lead if us__name is blank
    """
    results = {"success": 0, "failed": [], "skipped": 0}

    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, start=2):
            try:
                lead_name = _upsert_crm_lead(row)
                _upsert_us_subscription(row, lead_name)
                frappe.db.commit()
                results["success"] += 1

            except Exception:
                frappe.db.rollback()
                error_msg = frappe.get_traceback()
                frappe.log_error(
                    title=f"Lead-US Import failed — Row {row_num}",
                    message=error_msg,
                )
                results["failed"].append(f"Row {row_num} | lead: {row.get('lead__name')} | {error_msg.splitlines()[-1]}")

    _print_summary(results)
    return results


# ──────────────────────────────────────────────
# CRM Lead upsert
# ──────────────────────────────────────────────
_LEAD_SKIP = {
    # system / read-only fields that must not be set manually
    "name", "naming_series",
}

_LEAD_FIELDS_TO_IMPORT = [
    "first_name", "middle_name", "last_name", "lead_name", "salutation",
    "gender", "custom_dob", "email", "mobile_no", "custom_secondary_email",
    "custom_alternate_mobile", "phone", "custom_address_line_1",
    "custom_address_line_2", "custom_city", "custom_state", "custom_postal_code",
    "custom_country", "custom_working_country", "organization", "job_title",
    "no_of_employees", "annual_revenue", "website", "industry", "territory",
    "status", "source", "lead_owner", "custom_lead_owner_emp",
    "custom_lead_owner_name", "custom_lead_medium", "converted",
    "custom_is_existing_customer", "custom_customer", "custom_description",
    "custom_entity", "custom_product", "custom_business_type", "custom_lead_date",
    "custom_client_category", "custom_residency", "custom_employee_status",
    "custom_client_indian_investments", "custom_client_intended_investment_in_us_market",
    "custom_event_date", "custom_event_location", "custom_event_type",
    "custom_rm_feedback", "custom_tl_feedback", "custom_bm_feedback",
    "custom_sales_rm", "custom_sales_rm_code", "custom_sales_rm_branch",
    "custom_sales_rm_team", "custom_aionion_client_code", "custom_service_rm",
    "custom_service_rm_name", "custom_lead_status_1", "custom_lead_status_2",
    "custom_insurance_remarks", "custom_pan_number", "custom_insurance_company",
    "custom_insurance_type", "custom_tenure", "custom_expiry_date",
    "custom_fresh_port", "custom_proposal_number", "custom_sum_assured",
    "custom_gross_premium", "custom_net_premium", "custom_policy_status",
    "custom_policy_number", "custom_mis_status", "custom_mis_verified_by",
    "custom_mis_verified_date", "custom_health_type", "custom_ped",
    "custom_ped_description", "custom_health_members", "custom_health_company",
    "custom_term_age", "custom_term_dob", "custom_term_occupation",
    "custom_term_itr", "custom_term_income", "custom_term_education",
    "custom_term_smoker", "custom_term_height", "custom_term_weight",
    "custom_term_company", "custom_motor_vehicle_year", "custom_motor_vehicle_type",
    "custom_motor_policy_copy", "custom_motor_company", "custom_travel_country",
    "custom_travel_duration", "custom_travel_members", "custom_travel_coverage",
    "custom_travel_company", "custom_parent_policy", "custom_parent_expiry_date",
    "custom_source_lead", "custom_renewal_company",
    "custom_bonds_number_of_units", "custom_bonds_amount",
    "custom_bonds_face_value", "custom_bonds_order_type", "custom_bonds_isin",
    "custom_bonds_company_name", "custom_bonds_execution_date",
    "custom_bonds_poa_status", "custom_bonds_client_confirmation",
    "custom_mf_investment_type", "custom_mf_scheme_name", "custom_mf_amount",
    "custom_mf_order_type", "custom_mf_ucc_code", "custom_mf_bank_name",
    "custom_mf_client_confirmation", "custom_equity_client_code",
    "custom_equity_pan", "custom_equity_account_type", "custom_equity_dp_id",
    "custom_equity_activation_date", "custom_us_payment_date",
    "custom_us_amount", "custom_us_subscription_type",
    "custom_us_mode_of_payment", "custom_us_quantity", "custom_us_currency",
    "custom_us_subscription_end_date", "sla", "sla_status",
    "facebook_lead_id", "facebook_form_id", "lost_reason", "lost_notes",
]


def _upsert_crm_lead(row):
    lead_doc_name = cstr(row.get("lead__name")).strip()

    exists = frappe.db.exists("CRM Lead", lead_doc_name) if lead_doc_name else False

    if exists:
        doc = frappe.get_doc("CRM Lead", lead_doc_name)
    else:
        doc = frappe.new_doc("CRM Lead")

    for fieldname in _LEAD_FIELDS_TO_IMPORT:
        raw = row.get(f"lead__{fieldname}")
        doc.set(fieldname, _cast_lead(fieldname, raw))

    if exists:
        # db_update → direct SQL UPDATE, bypasses all Python validation
        # needed for: stale Select values, broken links, missing mandatory fields
        doc.db_update()
    else:
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links = True
        doc.db_insert()

    return doc.name


# ──────────────────────────────────────────────
# US Subscription Record upsert
# ──────────────────────────────────────────────
_US_FIELDS_TO_IMPORT = [
    "lead", "task", "customer", "company", "client_status", "branch",
    "department", "subscription_type", "mode_of_payment", "chola_client_code",
    "quantity", "currency", "subscription_end_date", "rm_employee_code",
    "rm_employee_name", "lead_entry_date", "data_entry_date", "email_address",
    "emp_code", "emp_name", "emp_team", "emp_branch", "alternate_email_id",
    "aionion_client_code", "client_name", "contact_number", "client_email",
    "intended_investment", "indian_investments", "country_of_residence",
    "country_code", "employment_status", "month", "year", "assigned_by",
    "eligibility", "us_status", "progress", "detailed_remarks", "reminder_date",
    "alternative_phone", "current_country", "alternative_email", "emp_phone",
    "new_email_id", "old_email_id", "mode_of_payment_new", "payment_date",
    "payment_month", "subscription_type_new", "client_status_new",
    "second_client_status", "quantity_new", "currency_new",
    "amount_paid_us_subs", "sub_start_month", "sub_end_month",
    "sub_start_date", "sub_end_date", "old_subscription_end_month",
    "old_subscription_month", "lead_source", "sales_done_by", "service_rm",
    "old_rm", "team", "email_sent", "risk_declaration", "payment_status",
    "us_remarks", "attended_webinar",
]


def _upsert_us_subscription(row, lead_name=None):
    us_doc_name = cstr(row.get("us__name")).strip()
    # Use passed lead_name (from newly created lead) or fall back to us__lead column
    lead_name = lead_name or cstr(row.get("us__lead")).strip()

    # If there is no US Subscription data at all for this row, skip
    if not us_doc_name and not lead_name:
        return

    # Find the existing record: first by us__name, then by lead link
    if us_doc_name and frappe.db.exists("US Subscription Record", us_doc_name):
        doc = frappe.get_doc("US Subscription Record", us_doc_name)
    elif lead_name:
        existing = frappe.db.get_value(
            "US Subscription Record", {"lead": lead_name}, "name"
        )
        if existing:
            doc = frappe.get_doc("US Subscription Record", existing)
        else:
            doc = frappe.new_doc("US Subscription Record")
    else:
        doc = frappe.new_doc("US Subscription Record")

    for fieldname in _US_FIELDS_TO_IMPORT:
        raw = row.get(f"us__{fieldname}")
        doc.set(fieldname, _cast_us(fieldname, raw))

    # Always override lead with the passed lead_name to ensure correct linking
    if lead_name:
        doc.lead = lead_name

    doc.flags.ignore_mandatory = True
    doc.flags.ignore_links = True
    doc.flags.ignore_validate = True

    if doc.is_new():
        doc.db_insert()
    else:
        # db_update → direct SQL UPDATE, bypasses all Python validation
        doc.db_update()


# ──────────────────────────────────────────────
def _print_summary(results):
    print(f"\n✅ Success : {results['success']}")
    print(f"❌ Failed  : {len(results['failed'])}")
    for msg in results["failed"]:
        print(f"   → {msg}")