import frappe
from frappe import _
from frappe.utils import today
from frappe.query_builder import DocType
from frappe.query_builder.functions import Count


@frappe.whitelist()
def get_renewals_rm_list(record_name):
    """Get all Renewals RMs with lead counts for round robin"""
    rm_users = frappe.get_all("Has Role",
        filters={"role": "Insurance Renewals RM", "parenttype": "User"},
        fields=["parent"])
    rm_user_ids = [r.parent for r in rm_users]

    employees = frappe.get_all("Employee",
        filters={"status": "Active", "user_id": ["in", rm_user_ids]},
        fields=["name", "employee_name", "user_id"])

    RNW = DocType("Insurance Renewal Record")
    emp_names = [e.name for e in employees]
    lead_counts = {}
    if emp_names:
        counts = (
            frappe.qb.from_(RNW)
            .select(RNW.renewals_rm, Count("*").as_("lead_count"))
            .where(
                (RNW.renewals_rm.isin(emp_names))
                & (RNW.docstatus == 0)
                & (RNW.renewal_status.isin(["Pending", "In Progress"]))
            )
            .groupby(RNW.renewals_rm)
        ).run(as_dict=True)
        lead_counts = {r.renewals_rm: r.lead_count for r in counts}

    all_rms = []
    best_rm = None
    best_count = float("inf")

    for emp in employees:
        count = lead_counts.get(emp.name, 0)
        all_rms.append({
            "employee": emp.name,
            "employee_name": emp.employee_name,
            "lead_count": count
        })
        if count < best_count:
            best_count = count
            best_rm = emp

    all_rms.sort(key=lambda x: x["lead_count"])

    suggested = {}
    if best_rm:
        suggested = {
            "employee": best_rm.name,
            "employee_name": best_rm.employee_name,
            "lead_count": best_count,
            "reason": "Round robin — fewest active renewals"
        }

    return {"suggested": suggested, "all_rms": all_rms}


@frappe.whitelist()
def assign_renewals_rm(record_name, renewals_rm):
    """Assign Renewals RM to renewal record"""
    doc = frappe.get_doc("Insurance Renewal Record", record_name)
    rm_name = frappe.db.get_value("Employee", renewals_rm, "employee_name")
    rm_user = frappe.db.get_value("Employee", renewals_rm, "user_id")

    doc.renewals_rm = renewals_rm
    doc.renewals_rm_name = rm_name
    doc.assigned_by = frappe.session.user
    doc.assigned_date = today()
    doc.renewal_status = "In Progress"
    doc.flags.ignore_permissions = True
    doc.save(ignore_permissions=True)

    # Share with Renewals RM
    if rm_user:
        existing = frappe.db.get_value("DocShare", {
            "share_doctype": "Insurance Renewal Record",
            "share_name": record_name,
            "user": rm_user
        }, "name")
        if not existing:
            frappe.share.add(
                doctype="Insurance Renewal Record",
                name=record_name,
                user=rm_user,
                read=1,
                write=1,
                share=0,
                flags={"ignore_share_permission": True}
            )

    frappe.db.commit()
    return {"renewals_rm": renewals_rm, "renewals_rm_name": rm_name}


@frappe.whitelist()
def approve_mis(record_name):
    """MIS approves renewal record"""
    _check_mis_role()
    doc = frappe.get_doc("Insurance Renewal Record", record_name)
    if doc.docstatus != 1:
        frappe.throw(_("MIS can only be verified on submitted records."))

    frappe.db.set_value("Insurance Renewal Record", record_name, {
        "mis_status": "Approved",
        "mis_verified_by": frappe.session.user,
        "mis_verified_date": today(),
    })
    frappe.db.commit()

    # Create next renewal record
    frappe.enqueue(
        "aionion_custom.aionion_custom.controllers.renewal_record.process_post_renewal_approval",
        record_name=record_name,
        queue="default"
    )
    return "Approved"


@frappe.whitelist()
def reject_mis(record_name):
    """MIS rejects renewal record — unlocks for Renewals RM to refill"""
    _check_mis_role()
    doc = frappe.get_doc("Insurance Renewal Record", record_name)
    if doc.docstatus != 1:
        frappe.throw(_("MIS can only be rejected on submitted records."))

    frappe.db.set_value("Insurance Renewal Record", record_name, {
        "mis_status": "Rejected",
        "mis_verified_by": frappe.session.user,
        "mis_verified_date": today(),
        "docstatus": 0
    })
    frappe.db.commit()
    return "Rejected"


def process_post_renewal_approval(record_name):
    """Create new Insurance Record + next Renewal Record after MIS approves"""
    try:
        doc = frappe.get_doc("Insurance Renewal Record", record_name)
        customer = frappe.get_doc("Customer", doc.customer)
        company = frappe.db.get_single_value("Global Defaults", "default_company")

        # Create new Insurance Record
        ins = frappe.get_doc({
            "doctype": "Insurance Record",
            "customer": doc.customer,
            "client_name": doc.client_name,
            "mobile_no": doc.mobile_no,
            "email": doc.email,
            "company": company,
            "insurance_products": doc.insurance_type,
            "insurance_company": doc.new_insurance_company or doc.insurance_company,
            "policy_number": doc.new_policy_number,
            "policy_status": doc.new_policy_status,
            "policy_expiry_date": doc.new_expiry_date,
            "gross_premium_value": doc.new_premium,
            "sum_insured": doc.new_sum_assured,
            "business_type": "Renewal",
            "transaction_type": "Sales",
            "custom_mis_status": "Approved",
        })
        ins.insert(ignore_permissions=True)

        # Create next renewal record
        if doc.new_expiry_date:
            next_renewal = frappe.get_doc({
                "doctype": "Insurance Renewal Record",
                "customer": doc.customer,
                "client_name": doc.client_name,
                "mobile_no": doc.mobile_no,
                "email": doc.email,
                "source_insurance_record": ins.name,
                "insurance_type": doc.insurance_type,
                "insurance_company": doc.new_insurance_company or doc.insurance_company,
                "existing_policy_number": doc.new_policy_number,
                "policy_expiry_date": doc.new_expiry_date,
                "renewal_status": "Pending",
                "mis_status": "Pending",
                "aionion_master_id": customer.custom_aionion_master_id,
            })
            next_renewal.insert(ignore_permissions=True)

            # Notify Dilip
            dilip_user = frappe.db.get_value("Has Role",
                {"role": "Insurance Renewals Manager", "parenttype": "User"},
                "parent") or "Administrator"
            notification = frappe.get_doc({
                "doctype": "Notification Log",
                "subject": "New Renewal Due: " + doc.client_name + " - " + (doc.insurance_type or ""),
                "email_content": "Policy renewed. Next renewal due: " + str(doc.new_expiry_date),
                "for_user": dilip_user,
                "type": "Alert",
                "document_type": "Insurance Renewal Record",
                "document_name": next_renewal.name,
            })
            notification.insert(ignore_permissions=True)

        frappe.db.commit()
        frappe.logger().info("Renewal approval processed: " + record_name)

    except Exception as e:
        frappe.log_error("Renewal approval error: " + str(e), "Renewal Record Error")


def _check_mis_role():
    user_roles = frappe.get_roles(frappe.session.user)
    if "Insurance MIS" not in user_roles and "System Manager" not in user_roles:
        frappe.throw(
            _("Only Insurance MIS role can verify or reject."),
            frappe.PermissionError
        )
