"""
Whitelisted API endpoints for CRM Lead + US Subscription import/export.
Place at: aionion_custom/aionion_custom/api/lead_us_import_export.py
"""

import csv
import io
import frappe
from frappe.utils.data import cstr, cint, flt, getdate, get_datetime

from aionion_custom.scripts.export_lead_us_subscription import LEAD_FIELDS, US_FIELDS
from aionion_custom.scripts.import_lead_us_subscription import (
    _cast_lead, _cast_us,
    _LEAD_FIELDS_TO_IMPORT, _US_FIELDS_TO_IMPORT,
    _print_summary,
)


@frappe.whitelist()
def export_csv():
    """
    Called from the UI. Streams the CSV as a file download.
    """
    from frappe.query_builder import DocType

    Lead  = DocType("CRM Lead")
    USSub = DocType("US Subscription Record")

    lead_selects = [getattr(Lead,  f).as_(f"lead__{f}") for f in LEAD_FIELDS]
    us_selects   = [getattr(USSub, f).as_(f"us__{f}")   for f in US_FIELDS]

    rows = (
        frappe.qb.from_(Lead)
        .left_join(USSub).on(USSub.lead == Lead.name)
        .select(*lead_selects, *us_selects)
        .run(as_dict=True)
    )

    fieldnames = [f"lead__{f}" for f in LEAD_FIELDS] + [f"us__{f}" for f in US_FIELDS]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: (v if v is not None else "") for k, v in row.items()})

    csv_content = output.getvalue().encode("utf-8")

    frappe.response["filename"]    = "lead_us_export.csv"
    frappe.response["filecontent"] = csv_content
    frappe.response["type"]        = "download"


@frappe.whitelist()
def import_csv(file_url):
    """
    Called from the UI after the user uploads a CSV via Frappe's file uploader.
    file_url: the /files/... URL returned by the uploader.
    """
    # Resolve the physical path from the Frappe file URL
    file_doc  = frappe.get_doc("File", {"file_url": file_url})
    file_path = file_doc.get_full_path()

    results = {"success": 0, "failed": [], "skipped": 0}

    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, start=2):
            try:
                _upsert_crm_lead(row)
                _upsert_us_subscription(row)
                frappe.db.commit()
                results["success"] += 1

            except Exception:
                frappe.db.rollback()
                error_msg = frappe.get_traceback()
                frappe.log_error(
                    title=f"Lead-US Import failed — Row {row_num}",
                    message=error_msg,
                )
                results["failed"].append(
                    f"Row {row_num} | lead: {row.get('lead__name')} | {error_msg.splitlines()[-1]}"
                )

    return results


# ── helpers (same logic as the console script) ────────────────────────────────

def _upsert_crm_lead(row):
    lead_doc_name = cstr(row.get("lead__name")).strip()
    if not lead_doc_name:
        return

    exists = frappe.db.exists("CRM Lead", lead_doc_name)

    if exists:
        doc = frappe.get_doc("CRM Lead", lead_doc_name)
    else:
        doc = frappe.new_doc("CRM Lead")

    for fieldname in _LEAD_FIELDS_TO_IMPORT:
        raw = row.get(f"lead__{fieldname}")
        doc.set(fieldname, _cast_lead(fieldname, raw))

    if exists:
        doc.db_update()
    else:
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links     = True
        doc.insert(ignore_permissions=True)


def _upsert_us_subscription(row):
    us_doc_name = cstr(row.get("us__name")).strip()
    lead_name   = cstr(row.get("us__lead")).strip()

    if not us_doc_name and not lead_name:
        return

    if us_doc_name and frappe.db.exists("US Subscription Record", us_doc_name):
        doc = frappe.get_doc("US Subscription Record", us_doc_name)
    elif lead_name:
        existing = frappe.db.get_value("US Subscription Record", {"lead": lead_name}, "name")
        doc = frappe.get_doc("US Subscription Record", existing) if existing else frappe.new_doc("US Subscription Record")
    else:
        doc = frappe.new_doc("US Subscription Record")

    for fieldname in _US_FIELDS_TO_IMPORT:
        raw = row.get(f"us__{fieldname}")
        doc.set(fieldname, _cast_us(fieldname, raw))

    if doc.is_new():
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links     = True
        doc.insert(ignore_permissions=True)
    else:
        doc.db_update()
