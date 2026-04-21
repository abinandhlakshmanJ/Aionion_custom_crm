import frappe
from frappe import _
from frappe.utils import today, add_days, getdate


def create_renewal_leads_for_expiring_policies():
    """
    PRD Section 9.1 — Renewal Scheduler
    Runs daily. Finds Insurance Records where policy expires in 60 days
    and no renewal lead exists yet. Creates renewal leads automatically.

    WHY 60 days:
    - Health/Term policies need 45+ days for underwriting
    - Motor policies need 30 days
    - 60 days gives buffer for all types
    """
    try:
        sixty_days_from_now = add_days(today(), 60)
        today_date = today()

        # Find policies expiring within 60 days with no renewal lead
        from frappe.query_builder import DocType
        IR = DocType("Insurance Record")
        CRMLead = DocType("CRM Lead")

        # Get expiring policies that don't have a renewal lead yet
        expiring = (
            frappe.qb.from_(IR)
            .select(
                IR.name,
                IR.customer,
                IR.client_name,
                IR.policy_number,
                IR.policy_expiry_date,
                IR.insurance_products,
                IR.insurance_company,
                IR.rm_employee_code,
                IR.lead,
            )
            .where(
                (IR.policy_expiry_date >= today_date)
                & (IR.policy_expiry_date <= sixty_days_from_now)
                & (IR.policy_status == "Issued")
                & (IR.custom_mis_status == "Approved")
            )
        ).run(as_dict=True)

        frappe.logger().info(
            f"Renewal Scheduler: Found {len(expiring)} expiring policies"
        )

        created = 0
        skipped = 0

        for policy in expiring:
            # Check if renewal lead already exists for this policy
            existing_renewal = frappe.db.get_value(
                "CRM Lead",
                {
                    "custom_parent_policy": policy.name,
                    "custom_product": "Insurance Renewals",
                    "docstatus": ["!=", 2]  # not cancelled
                },
                "name"
            )

            if existing_renewal:
                skipped += 1
                continue

            # Get customer details
            customer = frappe.get_doc("Customer", policy.customer)

            # Get dilip user
            dilip_user = "Administrator"

            # Get original lead details if available
            mobile = customer.custom_mobile or ""
            email = customer.custom_email or ""
            residency = customer.custom_residency or "Indian"
            client_category = "Aionion Client"

            # Parse first/last name
            parts = (policy.client_name or "").split(" ", 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""

            renewal = frappe.get_doc({
                "doctype": "CRM Lead",
                "first_name": first_name,
                "last_name": last_name,
                "lead_name": policy.client_name,
                "mobile_no": mobile,
                "email": email,
                "custom_entity": "Aionion Insurance",
                "custom_product": "Insurance Renewals",
                "custom_business_type": "Renewal",
                "custom_client_category": client_category,
                "custom_residency": residency,
                "custom_insurance_type": policy.insurance_products,
                "custom_customer": policy.customer,
                "custom_parent_policy": policy.name,
                "custom_parent_expiry_date": policy.policy_expiry_date,
                "custom_source_lead": policy.lead,
                "custom_renewal_company": policy.insurance_company,
                "custom_sales_rm": policy.rm_employee_code,
                "lead_owner": dilip_user,
                "status": "New",
            })
            renewal.insert(ignore_permissions=True)
            created += 1

            # Notify Dilip
            try:
                notification = frappe.get_doc({
                    "doctype": "Notification Log",
                    "subject": f"Renewal Due: {policy.client_name} - {policy.insurance_products}",
                    "email_content": (
                        f"Policy {policy.policy_number} for {policy.client_name} "
                        f"expires on {policy.policy_expiry_date}. "
                        f"Renewal lead {renewal.name} created automatically."
                    ),
                    "for_user": dilip_user,
                    "type": "Alert",
                    "document_type": "CRM Lead",
                    "document_name": renewal.name,
                })
                notification.insert(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(
                    f"Renewal notification error: {str(e)}",
                    "Renewal Scheduler Notification"
                )

        frappe.db.commit()
        frappe.logger().info(
            f"Renewal Scheduler: Created {created} leads, Skipped {skipped} (already exist)"
        )

    except Exception as e:
        frappe.log_error(
            f"Renewal Scheduler Error: {str(e)}",
            "Renewal Scheduler"
        )
