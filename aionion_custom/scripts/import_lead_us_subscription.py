"""
Import script: CRM Lead (US entity) + US Subscription Record
Place at:
  aionion_custom/aionion_custom/scripts/import_lead_us_subscription.py
"""

import csv
import frappe
from frappe.utils import cstr, cint, flt, getdate

from aionion_custom.aionion_custom.scripts.export_lead_us_subscription import (
    LEAD_FIELDS,
    US_FIELDS,
)

# ── Field type maps ────────────────────────────────────────────────────────
_LEAD_DATE_FIELDS = {
    "custom_lead_date", "custom_dob",
    "custom_us_subscription_end_date", "custom_us_payment_date",
}
_LEAD_INT_FIELDS   = {"custom_us_quantity"}
_LEAD_FLOAT_FIELDS = {"custom_us_amount"}
_LEAD_CHECK_FIELDS = {"custom_is_existing_customer"}

_US_DATETIME_FIELDS = {"data_entry_date", "lead_entry_date"}
_US_DATE_FIELDS = {
    "payment_date", "reminder_date", "sub_start_date", "sub_end_date",
}
_US_INT_FIELDS   = {"quantity_new", "quantity"}
_US_FLOAT_FIELDS = {"amount_paid_us_subs"}

_LEAD_SKIP_ON_UPDATE = {"name", "creation", "modified"}
_US_SKIP_ON_UPDATE   = {"name", "lead", "creation", "modified"}


def _cast_lead(fieldname, value):
    if value is None or cstr(value).strip() == "":
        return None
    if fieldname in _LEAD_DATE_FIELDS:
        try:
            return getdate(cstr(value))
        except Exception:
            return None
    if fieldname in _LEAD_INT_FIELDS:
        return cint(value) or None
    if fieldname in _LEAD_FLOAT_FIELDS:
        return flt(value) or None
    if fieldname in _LEAD_CHECK_FIELDS:
        return 1 if cstr(value).strip().lower() in ("1", "yes", "true") else 0
    return cstr(value).strip() or None


def _cast_us(fieldname, value):
    if value is None or cstr(value).strip() == "":
        return None
    if fieldname in _US_DATETIME_FIELDS:
        try:
            return frappe.utils.get_datetime(cstr(value))
        except Exception:
            return None
    if fieldname in _US_DATE_FIELDS:
        try:
            return getdate(cstr(value))
        except Exception:
            return None
    if fieldname in _US_INT_FIELDS:
        return cint(value) or None
    if fieldname in _US_FLOAT_FIELDS:
        return flt(value) or None
    return cstr(value).strip() or None


def _read_csv(file_path):
    """
    Reads CSV handling both formats:
    - Two-row header: Row 1 = display labels, Row 2 = fieldnames → use Row 2 as keys
    - Single-row header: Row 1 = fieldnames (lead__x / us__x)
    """
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        all_rows = list(reader)

    if not all_rows:
        return []

    row1 = all_rows[0]
    row2 = all_rows[1] if len(all_rows) > 1 else []

    # Detect two-row header: row2 starts with "lead__" or "us__" values
    is_two_row = row2 and any(
        str(v).startswith("lead__") or str(v).startswith("us__")
        for v in row2
    )

    if is_two_row:
        headers  = row2       # actual fieldnames
        data_rows = all_rows[2:]
    else:
        headers  = row1       # single-row fieldnames
        data_rows = all_rows[1:]

    return [dict(zip(headers, row)) for row in data_rows if any(v.strip() for v in row)]


def _upsert_crm_lead(row):
    existing_name = cstr(row.get("lead__name", "")).strip()

    if existing_name and frappe.db.exists("CRM Lead", existing_name):
        doc = frappe.get_doc("CRM Lead", existing_name)
        for f in LEAD_FIELDS:
            if f in _LEAD_SKIP_ON_UPDATE:
                continue
            val = _cast_lead(f, row.get(f"lead__{f}"))
            if val is not None:
                doc.set(f, val)
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links     = True
        doc.flags.ignore_validate  = True
        doc.db_update()
        return doc.name

    # New lead
    doc = frappe.new_doc("CRM Lead")
    for f in LEAD_FIELDS:
        if f in ("name", "creation", "modified"):
            continue
        val = _cast_lead(f, row.get(f"lead__{f}"))
        if val is not None:
            doc.set(f, val)

    if not doc.custom_entity:
        doc.custom_entity = "Aionion Global"

    doc.flags.ignore_mandatory = True
    doc.flags.ignore_links     = True
    doc.flags.ignore_validate  = True
    doc.db_insert()
    frappe.db.commit()
    return doc.name


def _upsert_us_subscription(row, lead_name):
    existing_name = cstr(row.get("us__name", "")).strip()

    if existing_name and frappe.db.exists("US Subscription Record", existing_name):
        doc = frappe.get_doc("US Subscription Record", existing_name)
        for f in US_FIELDS:
            if f in _US_SKIP_ON_UPDATE:
                continue
            val = _cast_us(f, row.get(f"us__{f}"))
            if val is not None:
                doc.set(f, val)
        doc.lead = lead_name
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links     = True
        doc.flags.ignore_validate  = True
        doc.db_update()
        return doc.name

    # Check by lead link to avoid duplicates
    existing_by_lead = frappe.db.get_value(
        "US Subscription Record", {"lead": lead_name}, "name"
    )
    if existing_by_lead:
        doc = frappe.get_doc("US Subscription Record", existing_by_lead)
        for f in US_FIELDS:
            if f in _US_SKIP_ON_UPDATE:
                continue
            val = _cast_us(f, row.get(f"us__{f}"))
            if val is not None:
                doc.set(f, val)
        doc.lead = lead_name
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links     = True
        doc.flags.ignore_validate  = True
        doc.db_update()
        return doc.name

    # New US Subscription Record
    doc = frappe.new_doc("US Subscription Record")
    doc.lead = lead_name
    for f in US_FIELDS:
        if f in ("name", "lead", "creation", "modified"):
            continue
        val = _cast_us(f, row.get(f"us__{f}"))
        if val is not None:
            doc.set(f, val)

    doc.flags.ignore_mandatory = True
    doc.flags.ignore_links     = True
    doc.flags.ignore_validate  = True
    doc.db_insert()
    frappe.db.commit()
    return doc.name


def import_records(file_path):
    """
    Main entry point. Reads CSV, upserts CRM Lead + US Subscription Record per row.
    Returns: {"success": int, "failed": list[str]}
    """
    rows    = _read_csv(file_path)
    success = 0
    failed  = []

    for i, row in enumerate(rows, start=1):
        try:
            lead_name = _upsert_crm_lead(row)
            has_us_data = any(
                cstr(row.get(f"us__{f}", "")).strip()
                for f in US_FIELDS
                if f not in ("name", "lead")
            )
            if has_us_data:
                _upsert_us_subscription(row, lead_name)
            success += 1
        except Exception as e:
            frappe.db.rollback()
            lead_id = (
                row.get("lead__name")
                or row.get("lead__email")
                or row.get("lead__first_name")
                or f"Row {i}"
            )
            failed.append(f"[Row {i}] {lead_id}: {str(e)}")

    return {"success": success, "failed": failed}