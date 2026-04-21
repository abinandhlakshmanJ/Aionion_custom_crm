import frappe
from frappe import _
from frappe.utils import today, now_datetime
import random
import string


def sync_lead_owner(doc, method):
    user_id = None
    if doc.custom_service_rm:
        user_id = frappe.db.get_value("Employee", doc.custom_service_rm, "user_id")
        if user_id:
            doc.lead_owner = user_id
            return
    # Only fall back to sales_rm if service_rm is not set
    if doc.custom_sales_rm and not doc.custom_service_rm:
        user_id = frappe.db.get_value("Employee", doc.custom_sales_rm, "user_id")
        if user_id:
            doc.lead_owner = user_id


def set_business_type(doc, method):
    product_map = {"Insurance Sales": "New Business", "Insurance Renewals": "Renewal"}
    if doc.custom_product in product_map:
        doc.custom_business_type = product_map[doc.custom_product]


def set_sales_rm_defaults(doc, method):
    # Set Sales RM to current user's employee if not already set
    if not doc.custom_sales_rm:
        employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
        if employee:
            doc.custom_sales_rm = employee

    # Service RM must NEVER be auto-set on creation
    # It must always be assigned manually via Assign Service RM button
    # NOTE: Sales RM and Service RM CAN be the same person — that is valid
    # We only prevent AUTO-setting service_rm, not manual assignment
    if doc.is_new():
        doc.custom_service_rm = None
        doc.custom_service_rm_name = None


def validate_insurance_fields(doc, method):
    if doc.custom_entity != "Aionion Insurance":
        return
    if doc.custom_policy_status == "Issued" and not doc.custom_policy_number:
        frappe.throw(_("Policy Number is mandatory when Policy Status is Issued."))


def before_submit_insurance_check(doc, method):
    if doc.custom_entity != "Aionion Insurance":
        return
    if doc.custom_policy_status == "Issued" and not doc.custom_policy_number:
        frappe.throw(_("Policy Number is mandatory before submitting when Policy Status is Issued."))
    if not doc.custom_policy_status:
        frappe.throw(_("Please set Policy Status before submitting."))


@frappe.whitelist()
def submit_insurance_lead(lead_name):
    doc = frappe.get_doc("CRM Lead", lead_name)
    if doc.docstatus != 0:
        frappe.throw(_("Lead is already submitted or cancelled."))
    before_submit_insurance_check(doc, None)
    # WHY ignore_permissions: CRM Lead submit permission is controlled
    # by our custom role logic. We check the user has the right role
    # via before_submit_insurance_check. The frappe submit permission
    # check is redundant and blocks valid Service RM users.
    doc.flags.ignore_permissions = True
    doc.submit()
    return "Submitted"


@frappe.whitelist()
def approve_mis(lead_name):
    _check_mis_role()
    doc = frappe.get_doc("CRM Lead", lead_name)
    if doc.docstatus != 1:
        frappe.throw(_("MIS verification can only be done after the lead is submitted."))
    doc.custom_mis_status = "Approved"
    doc.custom_mis_verified_by = frappe.session.user
    doc.custom_mis_verified_date = today()
    doc.save(ignore_permissions=True)
    frappe.msgprint(_("MIS Approved for {0}. Customer creation in progress...").format(lead_name), indicator="green")
    frappe.enqueue(
        "aionion_custom.aionion_custom.controllers.crm_lead.process_post_mis_approval",
        lead_name=lead_name,
        queue="default",
        timeout=300
    )
    return "Approved"


@frappe.whitelist()
def reject_mis(lead_name):
    _check_mis_role()
    doc = frappe.get_doc("CRM Lead", lead_name)
    if doc.docstatus != 1:
        frappe.throw(_("MIS verification can only be done after the lead is submitted."))

    # Simply unlock the lead back to draft so Service RM can refill and resubmit
    # WHY direct SQL: frappe.db.set_value is the cleanest way to update
    # a submitted document's fields without triggering hooks
    frappe.db.set_value("CRM Lead", lead_name, "custom_mis_status", "Rejected")
    frappe.db.set_value("CRM Lead", lead_name, "custom_mis_verified_by", frappe.session.user)
    frappe.db.set_value("CRM Lead", lead_name, "custom_mis_verified_date", today())
    frappe.db.set_value("CRM Lead", lead_name, "docstatus", 0)
    frappe.db.commit()

    frappe.msgprint(
        _("MIS Rejected for {0}. Lead unlocked — Service RM can now refill and resubmit.").format(lead_name),
        indicator="red"
    )
    return "Rejected"


def process_post_mis_approval(lead_name):
    try:
        lead = frappe.get_doc("CRM Lead", lead_name)
        customer = _get_or_create_customer(lead)
        if not customer.custom_aionion_master_id:
            _generate_aionion_master_id(customer)
        ins_record = _create_insurance_record(lead, customer)
        renewal_lead = _create_renewal_lead(lead, customer, ins_record)
        _notify_renewals_manager(renewal_lead, lead)
        frappe.db.commit()
        frappe.logger().info("Phase4 Complete for lead " + lead_name)
    except Exception as e:
        frappe.log_error("Phase4 Error for lead " + lead_name + ": " + str(e), "Post MIS Approval Error")


def _get_or_create_customer(lead):
    existing_customer = None
    if lead.custom_pan_number:
        existing_customer = frappe.db.get_value("Customer", {"pan": lead.custom_pan_number}, "name")
    if not existing_customer and lead.mobile_no:
        existing_customer = frappe.db.get_value("Customer", {"custom_mobile": lead.mobile_no}, "name")
    if existing_customer:
        frappe.db.set_value("CRM Lead", lead.name, "custom_customer", existing_customer, update_modified=False)
        return frappe.get_doc("Customer", existing_customer)
    company = frappe.db.get_single_value("Global Defaults", "default_company")
    customer = frappe.get_doc({
        "doctype": "Customer",
        "customer_name": lead.lead_name,
        "customer_type": "Individual",
        "customer_group": "Individual",
        "territory": "India",
        "custom_mobile": lead.mobile_no,
        "custom_email": lead.email,
        "custom_dob": lead.custom_dob,
        "custom_residency": lead.custom_residency,
        "pan": lead.custom_pan_number,
        "custom_relationship_manager": lead.custom_sales_rm,
        "custom_service_rm": lead.custom_service_rm,
        "custom_account_category": "NRI" if lead.custom_residency == "NRI" else "Individual",
    })
    customer.insert(ignore_permissions=True)
    frappe.db.commit()
    frappe.db.set_value("CRM Lead", lead.name, "custom_customer", customer.name, update_modified=False)
    return customer


def _generate_aionion_master_id(customer):
    chars = [c for c in string.ascii_uppercase + string.digits if c not in ("0","O","1","I","L")]
    random_part = "".join(random.choices(chars, k=4))
    year = str(now_datetime().year)[2:]
    seq = frappe.db.count("Customer", {"custom_aionion_master_id": ["like", "AIO-" + year + "-%"]}) + 1
    aio_id = "AIO-" + year + "-" + random_part + "-" + str(seq).zfill(6)
    customer.custom_aionion_master_id = aio_id
    customer.custom_random_part = random_part
    customer.save(ignore_permissions=True)
    frappe.db.commit()


def _create_insurance_record(lead, customer):
    existing = frappe.db.get_value("Insurance Record", {"lead": lead.name}, "name")
    if existing:
        return frappe.get_doc("Insurance Record", existing)
    company = frappe.db.get_single_value("Global Defaults", "default_company")
    rm_branch = frappe.db.get_value("Employee", lead.custom_sales_rm, "branch") if lead.custom_sales_rm else None
    rm_dept = frappe.db.get_value("Employee", lead.custom_sales_rm, "department") if lead.custom_sales_rm else None
    ins = frappe.get_doc({
        "doctype": "Insurance Record",
        "lead": lead.name,
        "customer": customer.name,
        "company": company,
        "client_name": lead.lead_name,
        "mobile_no": lead.mobile_no,
        "email": lead.email,
        "pan": lead.custom_pan_number,
        "rm_employee_code": lead.custom_service_rm or lead.custom_sales_rm,
        "branch": rm_branch,
        "department": rm_dept,
        "transaction_type": "Sales",
        "business_type": lead.custom_business_type or "New Business",
        "insurance_products": lead.custom_insurance_type,
        "insurance_company": lead.custom_insurance_company,
        "proposal_number": lead.custom_proposal_number,
        "sum_insured": lead.custom_sum_assured,
        "gross_premium_value": lead.custom_gross_premium,
        "net_premium_value": lead.custom_net_premium,
        "policy_number": lead.custom_policy_number,
        "policy_status": lead.custom_policy_status,
        "policy_expiry_date": lead.custom_expiry_date,
        "custom_tenure": lead.custom_tenure,
        "custom_type_fresh_port": lead.custom_fresh_port,
        "custom_mis_status": "Approved",
    })
    ins.insert(ignore_permissions=True)
    frappe.db.commit()
    return ins


def _create_renewal_lead(lead, customer, ins_record):
    # Get Renewals Manager — user with Insurance Renewals Manager role
    dilip_user = frappe.db.get_value("Has Role",
        {"role": "Insurance Renewals Manager", "parenttype": "User"},
        "parent") or "Administrator"
    # Parse first_name from lead_name
    name_parts = (lead.lead_name or "").split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    renewal = frappe.get_doc({
        "doctype": "CRM Lead",
        "first_name": first_name,
        "last_name": last_name,
        "lead_name": lead.lead_name,
        "mobile_no": lead.mobile_no,
        "email": lead.email,
        "custom_entity": "Aionion Insurance",
        "custom_product": "Insurance Renewals",
        "custom_business_type": "Renewal",
        "custom_client_category": lead.custom_client_category,
        "custom_residency": lead.custom_residency,
        "custom_insurance_type": lead.custom_insurance_type,
        "custom_customer": customer.name,
        "custom_parent_policy": ins_record.name,
        "custom_parent_expiry_date": lead.custom_expiry_date,
        "custom_source_lead": lead.name,
        "custom_renewal_company": lead.custom_insurance_company,
        "custom_sales_rm": lead.custom_service_rm or lead.custom_sales_rm,
        "lead_owner": dilip_user,
        "status": "New",
    })
    renewal.insert(ignore_permissions=True)
    frappe.db.commit()
    return renewal


def _notify_renewals_manager(renewal_lead, original_lead):
    # Get Renewals Manager — user with Insurance Renewals Manager role
    dilip_user = frappe.db.get_value("Has Role",
        {"role": "Insurance Renewals Manager", "parenttype": "User"},
        "parent") or "Administrator"
    expiry = str(original_lead.custom_expiry_date or "N/A")
    insurance_type = original_lead.custom_insurance_type or "Insurance"
    try:
        notification = frappe.get_doc({
            "doctype": "Notification Log",
            "subject": "New Renewal Lead: " + original_lead.lead_name + " - " + insurance_type,
            "email_content": "New renewal lead for " + original_lead.lead_name + ". Type: " + insurance_type + ". Expires: " + expiry,
            "for_user": dilip_user,
            "type": "Alert",
            "document_type": "CRM Lead",
            "document_name": renewal_lead.name,
        })
        notification.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error("Notification error: " + str(e), "Renewal Notification")




@frappe.whitelist()
def get_suggested_service_rm(lead_name):
    """
    Phase 5 — PRD Section 6
    Round-robin assignment logic.
    Priority order:
    1. Client already has an Insurance lead with a Service RM → use same RM
    2. New client → assign to RM with fewest active Insurance leads
    """
    lead = frappe.get_doc("CRM Lead", lead_name)

    # ── Priority Chain ──────────────────────────────────────────────────────
    # 1. PAN match (most accurate — unique identifier)
    # 2. Mobile + Name match (high confidence)
    # 3. Mobile only (medium confidence)
    # 4. Round robin (new client)
    # Always suggest + confirm — never auto-assign

    from frappe.query_builder import DocType
    CRMLead = DocType("CRM Lead")

    def find_existing_rm(filters, reason):
        query = (
            frappe.qb.from_(CRMLead)
            .select(CRMLead.custom_service_rm)
            .where(
                (CRMLead.custom_service_rm.isnotnull())
                & (CRMLead.custom_entity == "Aionion Insurance")
                & (CRMLead.custom_product != "Insurance Renewals")
                & (CRMLead.name != lead_name)
                & (CRMLead.docstatus != 2)
            )
        )
        for field, value in filters.items():
            query = query.where(getattr(CRMLead, field) == value)
        result = query.orderby(CRMLead.creation, order=frappe.qb.desc).limit(1).run(as_dict=True)
        if result and result[0].get("custom_service_rm"):
            rm = result[0]["custom_service_rm"]
            rm_name = frappe.db.get_value("Employee", rm, "employee_name")
            return {"service_rm": rm, "service_rm_name": rm_name, "reason": reason}
        return None

    # Priority 1: PAN match (Service RM fills PAN — most reliable)
    if lead.custom_pan_number:
        match = find_existing_rm(
            {"custom_pan_number": lead.custom_pan_number},
            "Same client — matched by PAN number"
        )
        if match:
            return match

    # Priority 2: Mobile + First Name match (cross-sell scenario)
    if lead.mobile_no and lead.first_name:
        match = find_existing_rm(
            {"mobile_no": lead.mobile_no, "first_name": lead.first_name},
            "Same client — matched by mobile + name"
        )
        if match:
            return match

    # Priority 3: Mobile only (same number, different product)
    if lead.mobile_no:
        match = find_existing_rm(
            {"mobile_no": lead.mobile_no},
            "Possible same client — matched by mobile number"
        )
        if match:
            return match

    # Priority 2: Round robin
    # Check if this is a renewal lead — use Renewals RM role
    # Otherwise use Service RM role
    lead_doc = frappe.get_doc("CRM Lead", lead_name)
    if lead_doc.custom_product == "Insurance Renewals":
        rm_role = "Insurance Renewals RM"
    else:
        rm_role = "Insurance Service RM"

    service_rm_users = frappe.get_all("Has Role",
        filters={"role": rm_role, "parenttype": "User"},
        fields=["parent"])
    service_rm_user_ids = [r.parent for r in service_rm_users]

    if not service_rm_user_ids:
        employees = frappe.get_all("Employee",
            filters={"status": "Active", "user_id": ["!=", ""]},
            fields=["name", "employee_name", "user_id"])
    else:
        employees = frappe.get_all("Employee",
            filters={"status": "Active", "user_id": ["in", service_rm_user_ids]},
            fields=["name", "employee_name", "user_id"])

    if not employees:
        return {"service_rm": None, "reason": "No Insurance Service RMs available"}

    # WHY frappe.qb not get_all in loop:
    # Count active leads per RM in ONE query — no N+1 problem
    from frappe.query_builder import DocType
    from frappe.query_builder.functions import Count
    CRMLead = DocType("CRM Lead")

    emp_names = [e.name for e in employees]
    lead_counts = (
        frappe.qb.from_(CRMLead)
        .select(CRMLead.custom_service_rm, Count("*").as_("lead_count"))
        .where(
            (CRMLead.custom_service_rm.isin(emp_names))
            & (CRMLead.custom_entity == "Aionion Insurance")
            & (CRMLead.docstatus == 0)
        )
        .groupby(CRMLead.custom_service_rm)
    ).run(as_dict=True)

    # Build count map
    count_map = {r.custom_service_rm: r.lead_count for r in lead_counts}

    # Find RM with lowest count
    best_rm = None
    best_count = float("inf")
    for emp in employees:
        count = count_map.get(emp.name, 0)
        if count < best_count:
            best_count = count
            best_rm = emp

    if best_rm:
        return {
            "service_rm": best_rm.name,
            "service_rm_name": best_rm.employee_name,
            "active_leads": best_count,
            "reason": "Round robin — fewest active leads"
        }

    return {"service_rm": None, "reason": "Could not determine Service RM"}


@frappe.whitelist()
def assign_service_rm(lead_name, service_rm):
    """
    Phase 5 — PRD Section 6.3
    Called when manager confirms Service RM assignment.
    Sets service_rm, syncs lead_owner, saves.
    Also shares lead with Sales RM so they don't lose visibility.
    """
    doc = frappe.get_doc("CRM Lead", lead_name)

    if doc.docstatus == 1:
        frappe.throw(_("Cannot assign Service RM on a submitted lead."))

    # Save Sales RM user before changing lead_owner
    sales_rm_user = None
    if doc.custom_sales_rm:
        sales_rm_user = frappe.db.get_value("Employee", doc.custom_sales_rm, "user_id")

    doc.custom_service_rm = service_rm
    rm_name = frappe.db.get_value("Employee", service_rm, "employee_name")
    doc.custom_service_rm_name = rm_name

    # Sync lead_owner to Service RM user
    service_rm_user = frappe.db.get_value("Employee", service_rm, "user_id")
    if service_rm_user:
        doc.lead_owner = service_rm_user

    doc.flags.ignore_permissions = True
    doc.save(ignore_permissions=True)

    # Share lead with original owner (Sales RM or Renewals Manager)
    # so they retain visibility after lead_owner changes to Service/Renewals RM
    users_to_share = []

    # Sales RM retains visibility
    if sales_rm_user and sales_rm_user != service_rm_user:
        users_to_share.append(sales_rm_user)

    # Renewals Manager (Dilip) retains visibility on renewal leads
    renewals_manager = frappe.db.get_value("Has Role",
        {"role": "Insurance Renewals Manager", "parenttype": "User"},
        "parent")
    if renewals_manager and renewals_manager != service_rm_user:
        users_to_share.append(renewals_manager)

    for share_user in users_to_share:
        existing_share = frappe.db.get_value("DocShare", {
            "share_doctype": "CRM Lead",
            "share_name": lead_name,
            "user": share_user
        }, "name")
        if not existing_share:
            frappe.share.add(
                doctype="CRM Lead",
                name=lead_name,
                user=share_user,
                read=1,
                write=1,
                share=0,
                flags={"ignore_share_permission": True}
            )

    frappe.db.commit()

    return {
        "service_rm": service_rm,
        "service_rm_name": rm_name,
        "message": "Service RM assigned successfully"
    }



@frappe.whitelist()
def get_renewals_rm_list(lead_name):
    """
    Returns suggested RM (round robin) + full list of all Renewals RMs
    with their current lead counts. Dilip can pick any RM manually.
    """
    from frappe.query_builder import DocType
    from frappe.query_builder.functions import Count

    # Get all Insurance Renewals RM users
    rm_users = frappe.get_all("Has Role",
        filters={"role": "Insurance Renewals RM", "parenttype": "User"},
        fields=["parent"])
    rm_user_ids = [r.parent for r in rm_users]

    employees = frappe.get_all("Employee",
        filters={"status": "Active", "user_id": ["in", rm_user_ids]},
        fields=["name", "employee_name", "user_id"])

    # Get lead counts per RM
    CRMLead = DocType("CRM Lead")
    emp_names = [e.name for e in employees]

    lead_counts = {}
    if emp_names:
        counts = (
            frappe.qb.from_(CRMLead)
            .select(CRMLead.custom_service_rm, Count("*").as_("lead_count"))
            .where(
                (CRMLead.custom_service_rm.isin(emp_names))
                & (CRMLead.custom_product == "Insurance Renewals")
                & (CRMLead.docstatus == 0)
            )
            .groupby(CRMLead.custom_service_rm)
        ).run(as_dict=True)
        lead_counts = {r.custom_service_rm: r.lead_count for r in counts}

    # Build full list with counts
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

    # Sort by lead count
    all_rms.sort(key=lambda x: x["lead_count"])

    suggested = {}
    if best_rm:
        suggested = {
            "employee": best_rm.name,
            "employee_name": best_rm.employee_name,
            "lead_count": best_count,
            "reason": "Round robin — fewest active renewal leads"
        }

    return {
        "suggested": suggested,
        "all_rms": all_rms
    }



def _create_renewal_record(lead, customer, ins_record):
    """
    PRD Section 7.5 — Create Insurance Renewal Record
    Separate doctype for Renewals team. Clean separation from Sales CRM Lead.
    """
    # Check if already exists
    existing = frappe.db.get_value("Insurance Renewal Record",
        {"source_insurance_record": ins_record.name}, "name")
    if existing:
        return frappe.get_doc("Insurance Renewal Record", existing)

    # Get Renewals Manager (Dilip)
    dilip_user = frappe.db.get_value("Has Role",
        {"role": "Insurance Renewals Manager", "parenttype": "User"},
        "parent") or "Administrator"

    renewal = frappe.get_doc({
        "doctype": "Insurance Renewal Record",
        "customer": customer.name,
        "client_name": lead.lead_name,
        "mobile_no": lead.mobile_no,
        "email": lead.email,
        "source_insurance_record": ins_record.name,
        "insurance_type": lead.custom_insurance_type,
        "insurance_company": lead.custom_insurance_company,
        "existing_policy_number": lead.custom_policy_number,
        "policy_expiry_date": lead.custom_expiry_date,
        "renewal_status": "Pending",
        "source_lead": lead.name,
        "aionion_master_id": customer.custom_aionion_master_id,
        "assigned_by": dilip_user,
        "assigned_date": frappe.utils.today(),
        "mis_status": "Pending",
    })
    renewal.insert(ignore_permissions=True)
    frappe.db.commit()
    return renewal

def _check_mis_role():
    user_roles = frappe.get_roles(frappe.session.user)
    if "Insurance MIS" not in user_roles and "System Manager" not in user_roles:
        frappe.throw(_("Only users with Insurance MIS role can verify or reject MIS status."), frappe.PermissionError)


@frappe.whitelist()
def get_current_user_roles():
    return frappe.get_roles(frappe.session.user)


def share_lead_with_mis_team(doc, method):
    """
    on_submit hook — PRD Section 10
    When a lead is submitted, automatically share it with all
    Insurance MIS role users so they can verify the policy.
    WHY DocShare and not just permissions:
    - Frappe CRM filters leads by lead_owner field
    - DocShare bypasses this filter for specific users
    - This is the standard Frappe approach for cross-user document access
    """
    if doc.custom_entity != "Aionion Insurance":
        return

    # Get all users with Insurance MIS role
    mis_users = frappe.get_all("Has Role",
        filters={"role": "Insurance MIS", "parenttype": "User"},
        fields=["parent"])

    for mis in mis_users:
        existing = frappe.db.get_value("DocShare", {
            "share_doctype": "CRM Lead",
            "share_name": doc.name,
            "user": mis.parent
        }, "name")

        if not existing:
            frappe.share.add(
                doctype="CRM Lead",
                name=doc.name,
                user=mis.parent,
                read=1,
                write=0,
                share=0,
                flags={"ignore_share_permission": True}
            )

    frappe.db.commit()
