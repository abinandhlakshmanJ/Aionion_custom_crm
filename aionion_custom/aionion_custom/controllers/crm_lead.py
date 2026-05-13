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

    # Auto-fill Sales RM details from Employee record
    if doc.custom_sales_rm:
        emp = frappe.db.get_value("Employee", doc.custom_sales_rm,
            ["name", "employee_name", "branch"],
            as_dict=True)
        if emp:
            doc.custom_sales_rm_code = emp.name
            if emp.branch:
                doc.custom_sales_rm_branch = emp.branch

    # Service RM must NEVER be auto-set on creation
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
        renewal_record = _create_renewal_record(lead, customer, ins_record)
        _notify_renewals_manager(renewal_record, lead)
        frappe.db.commit()
        frappe.logger().info("Phase4 Complete for lead " + lead_name)
    except Exception as e:
        frappe.log_error("Phase4 Error for lead " + lead_name + ": " + str(e), "Post MIS Approval Error")


def _get_or_create_customer(lead):
    existing_customer = None

    # Rule: Only match on PAN — PAN is unique per individual in India
    # Mobile alone is NOT enough — family members share phones
    # Example: Father's insurance + Son's demat → same mobile, different PAN → different customers
    if lead.custom_pan_number:
        existing_customer = frappe.db.get_value("Customer", {"pan": lead.custom_pan_number}, "name")
        if existing_customer:
            frappe.db.set_value("CRM Lead", lead.name, "custom_customer", existing_customer, update_modified=False)
            return frappe.get_doc("Customer", existing_customer)

    # No PAN match → always create new customer
    # Even if mobile matches — could be family member
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
            "subject": "New Renewal: " + original_lead.lead_name + " - " + insurance_type + " expires " + expiry,
            "email_content": "New renewal record for " + original_lead.lead_name + ". Type: " + insurance_type + ". Expires: " + expiry,
            "for_user": dilip_user,
            "type": "Alert",
            "document_type": "Insurance Renewal Record",
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
    # Determine role and entity based on product/entity
    lead_doc = frappe.get_doc("CRM Lead", lead_name)

    if lead_doc.custom_entity == "US Subscription":
        rm_role = "US Subscription RM"
        filter_entity = "US Subscription"
    elif lead_doc.custom_product == "Insurance Renewals":
        rm_role = "Insurance Renewals RM"
        filter_entity = "Aionion Insurance"
    else:
        rm_role = "Insurance Service RM"
        filter_entity = "Aionion Insurance"

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
        return {"service_rm": None, "reason": f"No {rm_role} available"}

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
            & (CRMLead.custom_entity == filter_entity)
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


@frappe.whitelist()
def get_my_team_employees(user=None):
    """
    Returns all employee IDs in the current user's hierarchy
    (themselves + all direct and indirect reportees)
    """
    if not user:
        user = frappe.session.user

    user_roles = frappe.get_roles(user)
    if "System Manager" in user_roles or user == "Administrator":
        all_emps = frappe.get_all("Employee", fields=["name"])
        return [e.name for e in all_emps]

    current_emps = frappe.get_all("Employee", filters={"user_id": user}, fields=["name"])
    if not current_emps:
        return []

    def get_reportees(emp_name, visited=None):
        if visited is None:
            visited = set()
        if emp_name in visited:
            return []
        visited.add(emp_name)
        result = [emp_name]
        for r in frappe.get_all("Employee", filters={"reports_to": emp_name}, fields=["name"]):
            result.extend(get_reportees(r.name, visited))
        return result

    team = set()
    for emp in current_emps:
        team.update(get_reportees(emp.name))
    return list(team)


@frappe.whitelist()
def get_user_ids_for_employees(employee_names):
    """Convert employee names to user IDs for lead filtering"""
    if not employee_names:
        return []
    employees = frappe.get_all("Employee",
        filters={"name": ["in", employee_names], "user_id": ["!=", ""]},
        fields=["user_id"])
    return [e.user_id for e in employees if e.user_id]



def get_permission_query_conditions(user=None):  # v3 - role-based entity filter
    if not user:
        user = frappe.session.user
    if user in ["Administrator", "administrator"]:
        return ""

    user_roles = frappe.get_roles(user)

    if "System Manager" in user_roles:
        return ""

    # US Subscription MIS — sees all US Subscription leads
    if "US Subscription MIS" in user_roles:
        return "`tabCRM Lead`.`custom_entity` = 'US Subscription'"

    # US Subscription RM — sees only their own US Subscription leads
    if "US Subscription RM" in user_roles and "Insurance Sales RM" not in user_roles and "Capital RM" not in user_roles:
        return ("`tabCRM Lead`.`custom_entity` = 'US Subscription' AND "
                "`tabCRM Lead`.`lead_owner` = '{}'".format(user))

    # Insurance MIS — sees all Insurance leads
    if "Insurance MIS" in user_roles:
        return "`tabCRM Lead`.`custom_entity` = 'Aionion Insurance'"

    # Hierarchy-based visibility for all other roles
    current_emps = frappe.get_all("Employee", filters={"user_id": user}, fields=["name"])
    if not current_emps:
        return "`tabCRM Lead`.`lead_owner` = '{}'".format(user)

    def get_reportees(emp_name, visited=None):
        if visited is None:
            visited = set()
        if emp_name in visited:
            return []
        visited.add(emp_name)
        result = [emp_name]
        for r in frappe.get_all("Employee", filters={"reports_to": emp_name}, fields=["name"]):
            result.extend(get_reportees(r.name, visited))
        return result

    team_emps = set()
    for emp in current_emps:
        team_emps.update(get_reportees(emp.name))

    team_users = frappe.get_all("Employee",
        filters={"name": ["in", list(team_emps)], "user_id": ["!=", ""]},
        fields=["user_id"])
    user_ids = list(set([u.user_id for u in team_users if u.user_id]))

    if not user_ids:
        return "`tabCRM Lead`.`lead_owner` = '{}'".format(user)
    return "`tabCRM Lead`.`lead_owner` in ('{}')".format("', '".join(user_ids))



def autoname_insurance_record(doc, method=None):
    """Generate INS-YY-XXXX-NNNNNN format ID"""
    import datetime
    import random
    import string

    yy = str(datetime.datetime.now().year)[2:]

    # Get random part from Customer
    random_part = ""
    if doc.customer:
        random_part = frappe.db.get_value(
            "Customer", doc.customer, "custom_random_part") or ""

    if not random_part:
        chars = [c for c in (string.ascii_uppercase + string.digits)
                 if c not in "0O1IL"]
        random_part = "".join(random.choices(chars, k=4))
        if doc.customer:
            frappe.db.set_value("Customer", doc.customer,
                "custom_random_part", random_part)

    from frappe.model.naming import make_autoname
    doc.name = make_autoname(
        "INS-" + yy + "-" + random_part + "-.######", doc=doc)


@frappe.whitelist()
def get_product_data(lead_name, product):
    """Get existing product record data for a lead"""
    product_doctype_map = {
        "US Subscription": "US Subscription Record",
        "Bonds": "Bonds Purchase Record",
        "Mutual Funds": "Mutual Funds Record",
        "Account Opening": "Equity Record"
    }
    dt = product_doctype_map.get(product)
    if not dt:
        return {}
    record = frappe.db.get_value(dt, {"lead": lead_name}, "*", as_dict=True)
    return record or {}


@frappe.whitelist()
def save_product_data(lead_name, product, data):
    """Save product-specific data to the respective doctype"""
    import json
    if isinstance(data, str):
        data = json.loads(data)

    product_doctype_map = {
        "US Subscription": "US Subscription Record",
        "Bonds": "Bonds Purchase Record",
        "Mutual Funds": "Mutual Funds Record",
        "Account Opening": "Equity Record"
    }
    dt = product_doctype_map.get(product)
    if not dt:
        frappe.throw(f"Unknown product: {product}")

    lead = frappe.get_doc("CRM Lead", lead_name)

    # Check if record exists
    existing = frappe.db.get_value(dt, {"lead": lead_name}, "name")
    if existing:
        rec = frappe.get_doc(dt, existing)
    else:
        rec = frappe.get_doc({
            "doctype": dt,
            "lead": lead_name,
            "customer": lead.get("custom_customer") or "",
            "client_name": lead.lead_name,
        })

    # Set fields from data
    for key, val in data.items():
        if hasattr(rec, key) and val:
            rec.set(key, val)

    if existing:
        rec.save(ignore_permissions=True)
    else:
        rec.insert(ignore_permissions=True)

    frappe.db.commit()
    return rec.name


@frappe.whitelist()
def submit_us_lead(lead_name):
    """Submit US Subscription lead for payment verification"""
    doc = frappe.get_doc("CRM Lead", lead_name)
    user_roles = frappe.get_roles(frappe.session.user)
    
    allowed_roles = ["US Subscription RM", "Insurance Sales RM", "Capital RM", 
                     "Global RM", "System Manager"]
    if not any(r in user_roles for r in allowed_roles):
        frappe.throw(_("Only Sales RM can submit US Subscription leads."))
    
    if doc.docstatus == 1:
        frappe.throw(_("Lead is already submitted."))
    
    doc.docstatus = 1
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    
    # Notify US Subscription MIS
    mis_users = frappe.get_all("Has Role",
        filters={"role": "US Subscription MIS", "parenttype": "User"},
        fields=["parent"])
    
    for mis in mis_users:
        try:
            frappe.get_doc({
                "doctype": "Notification Log",
                "subject": f"US Lead Submitted: {doc.lead_name} — Verify Payment",
                "email_content": f"US Subscription lead {lead_name} submitted by {frappe.session.user}. Please verify payment.",
                "for_user": mis.parent,
                "type": "Alert",
                "document_type": "CRM Lead",
                "document_name": lead_name,
            }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(str(e), "US Lead Submit Notification Error")
    
    frappe.db.commit()
    return "Submitted"


@frappe.whitelist()
def verify_us_payment(lead_name):
    """MIS verifies payment — creates Customer + US Subscription Record"""
    user_roles = frappe.get_roles(frappe.session.user)
    if "US Subscription MIS" not in user_roles and "System Manager" not in user_roles:
        frappe.throw(_("Only US Subscription MIS can verify payments."))
    
    doc = frappe.get_doc("CRM Lead", lead_name)
    
    if doc.docstatus != 1:
        frappe.throw(_("Lead must be submitted before payment verification."))
    
    # Update payment status — only fields that exist in CRM Lead
    frappe.db.set_value("CRM Lead", lead_name, {
        "custom_mis_status": "Approved",
        "custom_mis_verified_by": frappe.session.user,
        "custom_mis_verified_date": frappe.utils.today(),
    })
    frappe.db.commit()
    
    # Process inline first then enqueue as backup
    try:
        process_us_post_approval(lead_name)
    except Exception as e:
        frappe.log_error(str(e), "US Post Approval Inline Error")
        frappe.enqueue(
            "aionion_custom.aionion_custom.controllers.crm_lead.process_us_post_approval",
            lead_name=lead_name,
            queue="default",
            timeout=300
        )
    return "Approved"


@frappe.whitelist()
def reject_us_payment(lead_name, reason=None):
    """MIS rejects payment"""
    user_roles = frappe.get_roles(frappe.session.user)
    if "US Subscription MIS" not in user_roles and "System Manager" not in user_roles:
        frappe.throw(_("Only US Subscription MIS can reject payments."))
    
    frappe.db.set_value("CRM Lead", lead_name, {
        "custom_mis_status": "Rejected",
        "custom_mis_verified_by": frappe.session.user,
        "custom_mis_verified_date": frappe.utils.today(),
    })
    
    # Unlock lead back to draft
    frappe.db.set_value("CRM Lead", lead_name, "docstatus", 0)
    frappe.db.commit()
    
    # Notify lead owner
    lead = frappe.get_doc("CRM Lead", lead_name)
    try:
        frappe.get_doc({
            "doctype": "Notification Log",
            "subject": f"US Payment Rejected: {lead.lead_name}",
            "email_content": f"Payment rejected. Reason: {reason or 'Not specified'}. Please update and resubmit.",
            "for_user": lead.lead_owner,
            "type": "Alert",
            "document_type": "CRM Lead",
            "document_name": lead_name,
        }).insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(str(e), "US Payment Reject Notification Error")
    
    frappe.db.commit()
    return "Rejected"


def process_us_post_approval(lead_name):
    """Background job — create Customer + US Subscription Record after payment approval"""
    try:
        lead = frappe.get_doc("CRM Lead", lead_name)
        
        # Get or create Customer
        customer = _get_or_create_customer(lead)
        if not customer.custom_aionion_master_id:
            _generate_aionion_master_id(customer)
        
        # Create US Subscription Record
        us_record = _create_us_subscription_record(lead, customer)
        
        # Link customer to US Subscription Record
        if us_record and customer:
            frappe.db.set_value("US Subscription Record", us_record.name, {
                "customer": customer.name,
                "payment_status": "Approved"
            })
            frappe.db.commit()
        # Lock lead
        frappe.db.set_value("CRM Lead", lead_name, "status", "Converted")
        frappe.db.commit()
        
        frappe.logger().info(f"US Post Approval Complete for {lead_name}")
    except Exception as e:
        frappe.log_error(f"US Post Approval Error for {lead_name}: {str(e)}", 
                         "US Post Approval Error")


def _create_us_subscription_record(lead, customer):
    """Create US Subscription Record from approved lead"""
    import datetime
    
    # Check if already exists
    existing = frappe.db.get_value("US Subscription Record", 
        {"lead": lead.name}, "name")
    if existing:
        return frappe.get_doc("US Subscription Record", existing)
    
    yy = str(datetime.datetime.now().year)[2:]
    random_part = customer.get("custom_random_part") or ""
    
    us_rec = frappe.get_doc({
        "doctype": "US Subscription Record",
        "customer": customer.name,
        "lead": lead.name,
        "client_name": lead.lead_name,
        "company": frappe.db.get_single_value("Global Defaults", "default_company"),
        "rm_employee_code": lead.custom_sales_rm,
        "rm_employee_name": frappe.db.get_value("Employee", lead.custom_sales_rm, "employee_name") if lead.custom_sales_rm else "",
        "client_status": "New",
        # Sales RM fields
        "email_address": lead.email,
        "contact_number": lead.mobile_no,
        "payment_status": "Approved",
    })
    us_rec.insert(ignore_permissions=True)
    frappe.db.commit()
    
    # Rename with correct format
    if random_part:
        new_name = f"US-{yy}-{random_part}-{us_rec.name.split('-')[-1].zfill(6)}"
        try:
            frappe.rename_doc("US Subscription Record", us_rec.name, new_name, 
                            ignore_permissions=True)
            frappe.db.commit()
        except Exception:
            pass
    
    return us_rec


@frappe.whitelist()
def get_us_subscription_details(lead_name):
    """Get US Subscription Details child table row for a lead"""
    lead = frappe.get_doc("CRM Lead", lead_name)
    details = lead.get("custom_us_subscription_details")
    if details and len(details) > 0:
        return details[0].as_dict()
    return {}


@frappe.whitelist()
def save_us_subscription_details(lead_name, data):
    """Save US Subscription Details child table for a lead"""
    import json
    if isinstance(data, str):
        data = json.loads(data)

    lead = frappe.get_doc("CRM Lead", lead_name)

    if lead.custom_us_subscription_details:
        # Update existing row
        row = lead.custom_us_subscription_details[0]
        for key, val in data.items():
            if hasattr(row, key):
                row.set(key, val)
    else:
        # Add new row
        lead.append("custom_us_subscription_details", data)

    lead.save(ignore_permissions=True)
    frappe.db.commit()
    return "Saved"


@frappe.whitelist()
def get_us_subscription_details(lead_name):
    """Get US Subscription Details child table row for a lead"""
    lead = frappe.get_doc("CRM Lead", lead_name)
    details = lead.get("custom_us_subscription_details")
    if details and len(details) > 0:
        return details[0].as_dict()
    return {}


@frappe.whitelist()
def save_us_subscription_details(lead_name, data):
    """Save US Subscription Details child table for a lead"""
    import json
    if isinstance(data, str):
        data = json.loads(data)

    lead = frappe.get_doc("CRM Lead", lead_name)

    if lead.custom_us_subscription_details:
        row = lead.custom_us_subscription_details[0]
        for key, val in data.items():
            if hasattr(row, key):
                row.set(key, val)
    else:
        lead.append("custom_us_subscription_details", data)

    lead.save(ignore_permissions=True)
    frappe.db.commit()
    return "Saved"


@frappe.whitelist()
def get_us_subscription_details(lead_name):
    lead = frappe.get_doc("CRM Lead", lead_name)
    details = lead.get("custom_us_subscription_details")
    if details and len(details) > 0:
        return details[0].as_dict()
    return {}


@frappe.whitelist()
def save_us_subscription_details(lead_name, data):
    import json
    if isinstance(data, str):
        data = json.loads(data)
    lead = frappe.get_doc("CRM Lead", lead_name)
    if lead.custom_us_subscription_details:
        row = lead.custom_us_subscription_details[0]
        for key, val in data.items():
            if hasattr(row, key):
                row.set(key, val)
    else:
        lead.append("custom_us_subscription_details", data)
    lead.save(ignore_permissions=True)
    frappe.db.commit()
    return "Saved"


@frappe.whitelist()
def create_us_subscription_from_lead(lead_name):
    """Create US Subscription Record pre-filled from Lead data"""
    existing = frappe.db.get_value("US Subscription Record", {"lead": lead_name}, "name")
    if existing:
        return existing

    lead = frappe.get_doc("CRM Lead", lead_name)

    rm_name = frappe.db.get_value("Employee", lead.custom_sales_rm, "employee_name") if lead.custom_sales_rm else ""

    rec = frappe.get_doc({
        "doctype": "US Subscription Record",
        "lead": lead_name,
        "client_name": lead.lead_name,
        "client_email": lead.email,
        "contact_number": lead.mobile_no,
        "email_address": lead.email,
        "country_of_residence": lead.custom_country,
        "employment_status": lead.custom_employee_status,
        "indian_investments": {"INR 25 Lakhs to 50 lakhs": "INR 25 Lakhs to 50 Lakhs"}.get(lead.custom_client_indian_investments, lead.custom_client_indian_investments),
        "intended_investment": lead.custom_client_intended_investment_in_us_market,
        "aionion_client_code": lead.custom_aionion_client_code,
        "emp_code": lead.custom_sales_rm_code,
        "emp_name": rm_name,
        "emp_branch": lead.custom_sales_rm_branch,
        "emp_team": lead.custom_sales_rm_team,
        "rm_employee_code": lead.custom_sales_rm,
        "rm_employee_name": rm_name,
        "client_status": "New",
        "payment_status": "Pending",
        "lead_source": lead.lead_source,
        "service_rm": lead.custom_service_rm,
        "new_email_id": lead.email,
        "lead_entry_date": lead.creation,
    })
    rec.insert(ignore_permissions=True)
    frappe.db.commit()
    return rec.name


@frappe.whitelist()
def create_us_subscription_from_lead(lead_name):
    existing = frappe.db.get_value("US Subscription Record", {"lead": lead_name}, "name")
    if existing:
        return existing
    lead = frappe.get_doc("CRM Lead", lead_name)
    rm_name = frappe.db.get_value("Employee", lead.custom_sales_rm, "employee_name") if lead.custom_sales_rm else ""
    rec = frappe.get_doc({
        "doctype": "US Subscription Record",
        "lead": lead_name,
        "client_name": lead.lead_name,
        "client_email": lead.email,
        "contact_number": lead.mobile_no,
        "email_address": lead.email,
        "country_of_residence": lead.custom_country,
        "employment_status": lead.custom_employee_status,
        "indian_investments": {"INR 25 Lakhs to 50 lakhs": "INR 25 Lakhs to 50 Lakhs"}.get(lead.custom_client_indian_investments, lead.custom_client_indian_investments),
        "intended_investment": lead.custom_client_intended_investment_in_us_market,
        "aionion_client_code": lead.custom_aionion_client_code,
        "emp_code": lead.custom_sales_rm_code,
        "emp_branch": lead.custom_sales_rm_branch,
        "rm_employee_code": lead.custom_sales_rm,
        "rm_employee_name": rm_name,
        "client_status": "New",
        "payment_status": "Pending",
        "lead_source": lead.lead_source,
        "service_rm": lead.custom_service_rm,
        "new_email_id": lead.email,
        "lead_entry_date": lead.creation,
    })
    rec.insert(ignore_permissions=True)
    frappe.db.commit()
    return rec.name


@frappe.whitelist()
def bulk_approve_us_payments(lead_names):
    import json
    if isinstance(lead_names, str):
        lead_names = json.loads(lead_names)

    user_roles = frappe.get_roles(frappe.session.user)
    if "US Subscription MIS" not in user_roles and "System Manager" not in user_roles:
        frappe.throw(_("Only US Subscription MIS can approve payments."))

    results = {"approved": [], "failed": [], "skipped": []}

    for lead_name in lead_names:
        try:
            lead = frappe.get_doc("CRM Lead", lead_name)

            # Skip non-US leads
            if lead.custom_entity != "US Subscription":
                results["skipped"].append(lead_name)
                continue

            # Skip non-submitted leads
            if lead.docstatus != 1:
                results["skipped"].append(lead_name)
                continue

            # Skip already approved
            if lead.custom_mis_status == "Approved":
                results["skipped"].append(lead_name)
                continue

            # Approve
            frappe.db.set_value("CRM Lead", lead_name, {
                "custom_mis_status": "Approved",
                "custom_mis_verified_by": frappe.session.user,
                "custom_mis_verified_date": frappe.utils.today(),
            })

            # Sync to US Subscription Record
            us_record = frappe.db.get_value("US Subscription Record",
                {"lead": lead_name}, "name")
            if us_record:
                frappe.db.set_value("US Subscription Record", us_record,
                    "payment_status", "Approved")

            results["approved"].append(lead_name)

            # Process in background
            frappe.enqueue(
                "aionion_custom.aionion_custom.controllers.crm_lead.process_us_post_approval",
                lead_name=lead_name,
                queue="default",
                timeout=300
            )

        except Exception as e:
            frappe.log_error(str(e), f"Bulk Approve Error: {lead_name}")
            results["failed"].append(lead_name)

    frappe.db.commit()
    return results


@frappe.whitelist()
def bulk_approve_us_payments(lead_names):
    import json
    if isinstance(lead_names, str):
        lead_names = json.loads(lead_names)

    user_roles = frappe.get_roles(frappe.session.user)
    if "US Subscription MIS" not in user_roles and "System Manager" not in user_roles:
        frappe.throw("Only US Subscription MIS can approve payments.")

    results = {"approved": [], "failed": [], "skipped": []}

    for lead_name in lead_names:
        try:
            lead = frappe.get_doc("CRM Lead", lead_name)
            if lead.custom_entity != "US Subscription":
                results["skipped"].append(lead_name)
                continue
            if lead.docstatus != 1:
                results["skipped"].append(lead_name)
                continue
            if lead.custom_mis_status == "Approved":
                results["skipped"].append(lead_name)
                continue

            frappe.db.set_value("CRM Lead", lead_name, {
                "custom_mis_status": "Approved",
                "custom_mis_verified_by": frappe.session.user,
                "custom_mis_verified_date": frappe.utils.today(),
            })

            us_record = frappe.db.get_value("US Subscription Record", {"lead": lead_name}, "name")
            if us_record:
                frappe.db.set_value("US Subscription Record", us_record, "payment_status", "Approved")

            results["approved"].append(lead_name)
            frappe.enqueue(
                "aionion_custom.aionion_custom.controllers.crm_lead.process_us_post_approval",
                lead_name=lead_name,
                queue="default",
                timeout=300
            )
        except Exception as e:
            frappe.log_error(str(e), "Bulk Approve Error")
            results["failed"].append(lead_name)

    frappe.db.commit()
    return results


@frappe.whitelist()
def send_us_subscription_expiry_notifications():
    """
    Scheduler job — runs daily
    Checks US Subscription Records expiring in 30 days
    Creates RNL lead and notifies Sales RM
    """
    from frappe.utils import today, add_days, getdate

    thirty_days_later = add_days(today(), 30)

    # Find US Subscription Records expiring in 30 days
    expiring_records = frappe.get_all("US Subscription Record",
        filters={
            "sub_end_date": ["between", [today(), thirty_days_later]],
            "payment_status": "Approved",
            "client_status_new": ["!=", "RNL"],
        },
        fields=[
            "name", "lead", "customer", "client_name",
            "email_address", "contact_number", "sub_end_date",
            "rm_employee_code", "sales_done_by", "subscription_type_new",
            "currency_new", "quantity_new"
        ]
    )

    for rec in expiring_records:
        try:
            # Check if RNL lead already exists for this record
            existing_rnl = frappe.db.get_value("CRM Lead", {
                "custom_entity": "US Subscription",
                "custom_client_category": original_lead.custom_client_category if original_lead else "Reference Client",
                "mobile_no": rec.contact_number,
                "status": ["!=", "Converted"]
            }, "name")

            if existing_rnl:
                continue

            # Get original lead details
            original_lead = frappe.get_doc("CRM Lead", rec.lead) if rec.lead else None

            # Get Sales RM and Service RM users
            sales_rm_user = None
            service_rm_user = None
            if rec.rm_employee_code:
                sales_rm_user = frappe.db.get_value("Employee",
                    rec.rm_employee_code, "user_id")
            if original_lead and original_lead.custom_service_rm:
                service_rm_user = frappe.db.get_value("Employee",
                    original_lead.custom_service_rm, "user_id")

            # Create RNL Lead
            name_parts = (rec.client_name or "").split(" ", 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            rnl_lead = frappe.get_doc({
                "doctype": "CRM Lead",
                "first_name": first_name,
                "last_name": last_name,
                "lead_name": rec.client_name,
                "email": rec.email_address,
                "mobile_no": rec.contact_number,
                "custom_entity": "US Subscription",
                "custom_product": "US Subscription",
                "custom_client_category": original_lead.custom_client_category if original_lead else "Reference Client",
                "custom_sales_rm": rec.rm_employee_code or (original_lead.custom_sales_rm if original_lead else None),
                "custom_service_rm": original_lead.custom_service_rm if original_lead else None,
                "custom_service_rm_name": original_lead.custom_service_rm_name if original_lead else None,
                "custom_country": original_lead.custom_country if original_lead else None,
                "custom_employee_status": original_lead.custom_employee_status if original_lead else None,
                "custom_client_indian_investments": original_lead.custom_client_indian_investments if original_lead else None,
                "custom_client_intended_investment_in_us_market": original_lead.custom_client_intended_investment_in_us_market if original_lead else None,
                "custom_aionion_client_code": original_lead.custom_aionion_client_code if original_lead else None,
                "custom_residency": original_lead.custom_residency if original_lead else "Indian",
                "custom_residency": original_lead.custom_residency if original_lead else "Indian",
                "lead_owner": service_rm_user or sales_rm_user or frappe.session.user,
                "status": "New",
            })
            rnl_lead.insert(ignore_permissions=True)
            frappe.db.commit()

            # Notify both Sales RM and Service RM
            notify_users = list(set(filter(None, [sales_rm_user, service_rm_user])))
            for notify_user in notify_users:
                try:
                    frappe.get_doc({
                        "doctype": "Notification Log",
                        "subject": f"US Subscription Expiring: {rec.client_name} — {rec.sub_end_date}",
                        "email_content": f"US Subscription for {rec.client_name} expires on {rec.sub_end_date}. RNL lead created: {rnl_lead.name}. Please follow up.",
                        "for_user": notify_user,
                        "type": "Alert",
                        "document_type": "CRM Lead",
                        "document_name": rnl_lead.name,
                    }).insert(ignore_permissions=True)
                    frappe.db.commit()
                except Exception:
                    pass

            frappe.logger().info(f"RNL Lead created for {rec.name}: {rnl_lead.name}")

        except Exception as e:
            frappe.log_error(
                f"Expiry Notification Error for {rec.name}: {str(e)}",
                "US Subscription Expiry Error"
            )


@frappe.whitelist()
def approve_us_subscription_payment(us_record_name):
    user_roles = frappe.get_roles(frappe.session.user)
    if "US Subscription Admin" not in user_roles and "System Manager" not in user_roles:
        frappe.throw("Only US Subscription Admin can approve payments.")

    rec = frappe.get_doc("US Subscription Record", us_record_name)
    rec.payment_status = "Approved"
    rec.save(ignore_permissions=True)

    # Notify lead owner
    if rec.lead:
        lead = frappe.get_doc("CRM Lead", rec.lead)
        frappe.db.set_value("CRM Lead", rec.lead, "custom_mis_status", "Approved")
        if lead.lead_owner:
            frappe.get_doc({
                "doctype": "Notification Log",
                "subject": f"Payment Approved: {rec.client_name}",
                "email_content": f"Payment for {rec.client_name} has been approved by {frappe.session.user}.",
                "for_user": lead.lead_owner,
                "type": "Alert",
                "document_type": "US Subscription Record",
                "document_name": us_record_name,
            }).insert(ignore_permissions=True)

    frappe.db.commit()
    return "Approved"


@frappe.whitelist()
def reject_us_subscription_payment(us_record_name, reason=None):
    user_roles = frappe.get_roles(frappe.session.user)
    if "US Subscription Admin" not in user_roles and "System Manager" not in user_roles:
        frappe.throw("Only US Subscription Admin can reject payments.")

    rec = frappe.get_doc("US Subscription Record", us_record_name)
    rec.payment_status = "Rejected"
    rec.save(ignore_permissions=True)

    # Notify lead owner
    if rec.lead:
        lead = frappe.get_doc("CRM Lead", rec.lead)
        frappe.db.set_value("CRM Lead", rec.lead, "custom_mis_status", "Rejected")
        if lead.lead_owner:
            frappe.get_doc({
                "doctype": "Notification Log",
                "subject": f"Payment Rejected: {rec.client_name}",
                "email_content": f"Payment for {rec.client_name} has been rejected. Reason: {reason or 'Not specified'}",
                "for_user": lead.lead_owner,
                "type": "Alert",
                "document_type": "US Subscription Record",
                "document_name": us_record_name,
            }).insert(ignore_permissions=True)

    frappe.db.commit()
    return "Rejected"


@frappe.whitelist()
def get_or_create_renewal_record(lead_name):
    """Get existing or create new Insurance Renewal Record for a renewal lead"""
    lead = frappe.get_cached_doc("CRM Lead", lead_name)

    existing = frappe.db.get_value("Insurance Renewal Record",
        {"source_lead": lead_name}, "name")
    if existing:
        return existing

    ins_record = None
    if lead.custom_parent_policy:
        ins_record = frappe.get_cached_doc("Insurance Record", lead.custom_parent_policy)

    doc = frappe.new_doc("Insurance Renewal Record")
    doc.source_lead       = lead_name
    doc.customer          = lead.custom_customer or None
    doc.client_name       = lead.lead_name
    doc.mobile_no         = lead.mobile_no
    doc.email             = lead.email
    doc.renewals_rm       = lead.custom_service_rm
    doc.aionion_master_id = lead.custom_aionion_client_code or None

    if ins_record:
        doc.source_insurance_record = ins_record.name
        doc.insurance_type          = ins_record.insurance_type or lead.custom_insurance_type
        doc.insurance_company       = ins_record.insurance_company
        doc.existing_policy_number  = ins_record.policy_number
        doc.policy_expiry_date      = ins_record.policy_expiry_date
    else:
        doc.insurance_type         = lead.custom_insurance_type
        doc.insurance_company      = lead.custom_renewal_company
        doc.existing_policy_number = None
        doc.policy_expiry_date     = lead.custom_parent_expiry_date

    doc.renewal_due_date = lead.custom_renewal_due_date or lead.custom_parent_expiry_date
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return doc.name


@frappe.whitelist()
def approve_renewal_mis(record_name):
    """MIS approves Insurance Renewal Record — updates Insurance Record with new policy"""
    _check_mis_role()
    rec = frappe.get_doc("Insurance Renewal Record", record_name)

    if rec.mis_status == "Approved":
        frappe.throw("Already approved.")

    rec.mis_status        = "Approved"
    rec.mis_verified_by   = frappe.session.user
    rec.mis_verified_date = frappe.utils.nowdate()
    rec.save(ignore_permissions=True)

    # Update source Insurance Record with new policy details
    if rec.source_insurance_record and rec.new_policy_number:
        ins = frappe.get_doc("Insurance Record", rec.source_insurance_record)
        if rec.new_policy_number:     ins.policy_number       = rec.new_policy_number
        if rec.new_insurance_company: ins.insurance_company   = rec.new_insurance_company
        if rec.new_expiry_date:       ins.policy_expiry_date  = rec.new_expiry_date
        if rec.new_premium:           ins.gross_premium_value = rec.new_premium
        if rec.new_sum_assured:       ins.sum_insured         = rec.new_sum_assured
        ins.save(ignore_permissions=True)

    # Update source CRM Lead renewal status
    if rec.source_lead:
        frappe.db.set_value("CRM Lead", rec.source_lead, "custom_renewal_status", "Renewed")

    frappe.db.commit()
    return {"status": "approved"}


@frappe.whitelist()
def reject_renewal_mis(record_name, reason=None):
    """MIS rejects Insurance Renewal Record"""
    _check_mis_role()
    rec = frappe.get_doc("Insurance Renewal Record", record_name)

    rec.mis_status        = "Rejected"
    rec.mis_verified_by   = frappe.session.user
    rec.mis_verified_date = frappe.utils.nowdate()
    if reason:
        rec.renewal_remarks = (rec.renewal_remarks or "") + f"\nRejected: {reason}"
    rec.save(ignore_permissions=True)

    if rec.source_lead:
        frappe.db.set_value("CRM Lead", rec.source_lead, "custom_renewal_status", "Pending")

    frappe.db.commit()
    return {"status": "rejected"}
