"""
Export CRM Lead + US Subscription Record to a single CSV.

Run via bench console:
    from aionion_custom.scripts.export_lead_us_subscription import export
    export("/home/frappe/frappe-bench/sites/airplane.local/private/files/lead_us_export.csv")
"""

import csv
import frappe
from frappe.query_builder import DocType


# ──────────────────────────────────────────────
# Exact CRM Lead fields (no UI-only types)
# ──────────────────────────────────────────────
LEAD_FIELDS = [
    "name",
    "naming_series",
    "first_name",
    "middle_name",
    "last_name",
    "lead_name",
    "salutation",
    "gender",
    "custom_dob",
    "email",
    "mobile_no",
    "custom_secondary_email",
    "custom_alternate_mobile",
    "phone",
    "custom_address_line_1",
    "custom_address_line_2",
    "custom_city",
    "custom_state",
    "custom_postal_code",
    "custom_country",
    "custom_working_country",
    "organization",
    "job_title",
    "no_of_employees",
    "annual_revenue",
    "website",
    "industry",
    "territory",
    "status",
    "source",
    "lead_owner",
    "custom_lead_owner_emp",
    "custom_lead_owner_name",
    "custom_lead_medium",
    "converted",
    "custom_is_existing_customer",
    "custom_customer",
    "custom_description",
    "custom_entity",
    "custom_product",
    "custom_business_type",
    "custom_lead_date",
    "custom_client_category",
    "custom_residency",
    "custom_employee_status",
    "custom_client_indian_investments",
    "custom_client_intended_investment_in_us_market",
    "custom_event_date",
    "custom_event_location",
    "custom_event_type",
    "custom_rm_feedback",
    "custom_tl_feedback",
    "custom_bm_feedback",
    "custom_sales_rm",
    "custom_sales_rm_code",
    "custom_sales_rm_branch",
    "custom_sales_rm_team",
    "custom_aionion_client_code",
    "custom_service_rm",
    "custom_service_rm_name",
    "custom_lead_status_1",
    "custom_lead_status_2",
    "custom_insurance_remarks",
    "custom_pan_number",
    "custom_insurance_company",
    "custom_insurance_type",
    "custom_tenure",
    "custom_expiry_date",
    "custom_fresh_port",
    "custom_proposal_number",
    "custom_sum_assured",
    "custom_gross_premium",
    "custom_net_premium",
    "custom_policy_status",
    "custom_policy_number",
    "custom_mis_status",
    "custom_mis_verified_by",
    "custom_mis_verified_date",
    "custom_health_type",
    "custom_ped",
    "custom_ped_description",
    "custom_health_members",
    "custom_health_company",
    "custom_term_age",
    "custom_term_dob",
    "custom_term_occupation",
    "custom_term_itr",
    "custom_term_income",
    "custom_term_education",
    "custom_term_smoker",
    "custom_term_height",
    "custom_term_weight",
    "custom_term_company",
    "custom_motor_vehicle_year",
    "custom_motor_vehicle_type",
    "custom_motor_policy_copy",
    "custom_motor_company",
    "custom_travel_country",
    "custom_travel_duration",
    "custom_travel_members",
    "custom_travel_coverage",
    "custom_travel_company",
    "custom_parent_policy",
    "custom_parent_expiry_date",
    "custom_source_lead",
    "custom_renewal_company",
    "custom_bonds_number_of_units",
    "custom_bonds_amount",
    "custom_bonds_face_value",
    "custom_bonds_order_type",
    "custom_bonds_isin",
    "custom_bonds_company_name",
    "custom_bonds_execution_date",
    "custom_bonds_poa_status",
    "custom_bonds_client_confirmation",
    "custom_mf_investment_type",
    "custom_mf_scheme_name",
    "custom_mf_amount",
    "custom_mf_order_type",
    "custom_mf_ucc_code",
    "custom_mf_bank_name",
    "custom_mf_client_confirmation",
    "custom_equity_client_code",
    "custom_equity_pan",
    "custom_equity_account_type",
    "custom_equity_dp_id",
    "custom_equity_activation_date",
    "custom_us_payment_date",
    "custom_us_amount",
    "custom_us_subscription_type",
    "custom_us_mode_of_payment",
    "custom_us_quantity",
    "custom_us_currency",
    "custom_us_subscription_end_date",
    "sla",
    "sla_status",
    "facebook_lead_id",
    "facebook_form_id",
    "lost_reason",
    "lost_notes",
]


# ──────────────────────────────────────────────
# Exact US Subscription Record fields (no UI-only types)
# ──────────────────────────────────────────────
US_FIELDS = [
    "name",
    "lead",                     # Link → CRM Lead  (join key)
    "task",
    "customer",
    "company",
    "client_status",
    "branch",
    "department",
    "subscription_type",
    "mode_of_payment",
    "chola_client_code",
    "quantity",
    "currency",
    "subscription_end_date",
    "rm_employee_code",
    "rm_employee_name",
    "lead_entry_date",
    "data_entry_date",
    "email_address",
    "emp_code",
    "emp_name",
    "emp_team",
    "emp_branch",
    "alternate_email_id",
    "aionion_client_code",
    "client_name",
    "contact_number",
    "client_email",
    "intended_investment",
    "indian_investments",
    "country_of_residence",
    "country_code",
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
    "current_country",
    "alternative_email",
    "emp_phone",
    "new_email_id",
    "old_email_id",
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
    "old_subscription_month",
    "lead_source",
    "sales_done_by",
    "service_rm",
    "old_rm",
    "team",
    "email_sent",
    "risk_declaration",
    "payment_status",
    "us_remarks",
    "attended_webinar",
]


def export(file_path):
    """
    Exports all CRM Leads joined with their US Subscription Record (if any).
    CSV columns are prefixed: lead__<fieldname> and us__<fieldname>
    """
    Lead = DocType("CRM Lead")
    USSub = DocType("US Subscription Record")

    # Build select list with explicit aliases to avoid column name conflicts
    lead_selects = [
        getattr(Lead, f).as_(f"lead__{f}") for f in LEAD_FIELDS
    ]
    us_selects = [
        getattr(USSub, f).as_(f"us__{f}") for f in US_FIELDS
    ]

    rows = (
        frappe.qb.from_(Lead)
        .left_join(USSub)
        .on(USSub.lead == Lead.name)
        .select(*lead_selects, *us_selects)
        .run(as_dict=True)
    )

    if not rows:
        print("No records found.")
        return

    fieldnames = [f"lead__{f}" for f in LEAD_FIELDS] + [f"us__{f}" for f in US_FIELDS]

    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: (v if v is not None else "") for k, v in row.items()})

    print(f"✅ Exported {len(rows)} records → {file_path}")
