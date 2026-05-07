import frappe
from frappe import _
from frappe.utils import today, add_days, getdate


def auto_create_us_renewal_leads():
    """
    Scheduler — runs daily
    Auto-creates renewal lead 30 days before US Subscription expiry
    """
    today_date = getdate(today())
    trigger_date = add_days(today_date, 30)

    # Find US Subscription Records expiring in 30 days
    expiring = frappe.get_all("US Subscription Record",
        filters={
            "sub_end_date": trigger_date,
            "client_status": "Active",
            "docstatus": ["!=", 2],
        },
        fields=["name", "customer", "client_name", "lead",
                "rm_employee_code", "rm_employee_name",
                "sub_end_date", "subscription_type_new",
                "currency_new", "amount_paid_us_subs"])

    for rec in expiring:
        # Skip if renewal lead already exists
        existing = frappe.db.get_value("CRM Lead", {
            "custom_entity": "US Subscription",
            "custom_product": "US Subscription",
            "custom_business_type": "Renewal",
            "custom_customer": rec.customer,
            "status": ["not in", ["Converted", "Dead"]],
        }, "name")

        if existing:
            frappe.logger().info(f"Renewal lead already exists for {rec.customer}: {existing}")
            continue

        try:
            # Get lead owner from original lead or RM
            lead_owner = frappe.db.get_value("CRM Lead", rec.lead, "lead_owner") if rec.lead else None
            if not lead_owner and rec.rm_employee_code:
                lead_owner = frappe.db.get_value("Employee", rec.rm_employee_code, "user_id")
            if not lead_owner:
                lead_owner = "Administrator"

            # Create renewal lead
            renewal_lead = frappe.get_doc({
                "doctype": "CRM Lead",
                "first_name": rec.client_name,
                "lead_owner": lead_owner,
                "custom_entity": "US Subscription",
                "custom_product": "US Subscription",
                "custom_business_type": "Renewal",
                "custom_customer": rec.customer,
                "custom_sales_rm": rec.rm_employee_code,
                "custom_sales_rm_name": rec.rm_employee_name,
                "status": "New",
                "source": "Renewal",
                "custom_us_payment_status": "Pending",
                "custom_us_sub_start_date": rec.sub_end_date,
            })
            renewal_lead.insert(ignore_permissions=True)
            frappe.db.commit()

            frappe.logger().info(f"✅ Renewal lead created: {renewal_lead.name} for {rec.customer}")

            # Notify US Subscription MIS
            mis_users = frappe.get_all("Has Role",
                filters={"role": "US Subscription MIS", "parenttype": "User"},
                fields=["parent"])

            for mis in mis_users:
                try:
                    frappe.get_doc({
                        "doctype": "Notification Log",
                        "subject": f"US Renewal Due: {rec.client_name} — expires {rec.sub_end_date}",
                        "email_content": f"US Subscription for {rec.client_name} expires on {rec.sub_end_date}. Renewal lead {renewal_lead.name} created.",
                        "for_user": mis.parent,
                        "type": "Alert",
                        "document_type": "CRM Lead",
                        "document_name": renewal_lead.name,
                    }).insert(ignore_permissions=True)
                except Exception as e:
                    frappe.log_error(str(e), "US Renewal Notification Error")

            frappe.db.commit()

        except Exception as e:
            frappe.log_error(
                f"Failed to create renewal lead for {rec.customer}: {str(e)}",
                "US Renewal Scheduler Error"
            )
