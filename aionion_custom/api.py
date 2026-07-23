import frappe
from frappe import _

@frappe.whitelist()
def send_custom_email(recipients, subject, content, cc=None, bcc=None, sender=None, attachments=None):
    if not recipients:
        frappe.throw(_("Recipients email address is required"))

    if isinstance(recipients, list):
        recipients_str = ", ".join(recipients)
    else:
        recipients_str = str(recipients)

    # Determine single shared outgoing email account
    shared_outgoing_email = frappe.db.get_value("Email Account", {"default_outgoing": 1}, "email_id")
    if not shared_outgoing_email:
        shared_outgoing_email = frappe.db.get_value("Email Account", {"enable_outgoing": 1}, "email_id")

    effective_sender = shared_outgoing_email or sender or frappe.session.user

    email_sent = False
    try:
        # Use frappe.sendmail with now=True to bypass 2-minute background queue and send IMMEDIATELY
        frappe.sendmail(
            recipients=recipients_str,
            cc=cc or "",
            bcc=bcc or "",
            subject=subject or "No Subject",
            message=content or "",
            sender=effective_sender,
            reply_to=frappe.session.user,
            attachments=attachments or [],
            now=True
        )
        email_sent = True
    except Exception as e:
        frappe.logger().warning(f"Immediate sendmail failed: {e}")

    # Ensure Communication record exists in MariaDB for Sent folder view
    existing = frappe.db.get_value(
        "Communication",
        {
            "sender": effective_sender,
            "recipients": recipients_str,
            "subject": subject or "No Subject",
            "sent_or_received": "Sent"
        },
        "name"
    )

    if not existing:
        doc = frappe.get_doc({
            "doctype": "Communication",
            "communication_type": "Communication",
            "communication_medium": "Email",
            "sent_or_received": "Sent",
            "sender": effective_sender,
            "recipients": recipients_str,
            "subject": subject or "No Subject",
            "content": content or "",
            "status": "Linked",
        })
        doc.insert(ignore_permissions=True)

    return {
        "status": "success",
        "email_sent": email_sent,
        "message": _("Email sent immediately")
    }


def route_incoming_email_to_rm(doc, method=None):
    """Auto-route incoming emails from central inbox to the assigned Lead RM"""
    if doc.sent_or_received != "Received" or not doc.sender:
        return

    sender_email = doc.sender.strip().lower()

    # 1. Search CRM Lead by primary or secondary email
    lead = frappe.db.get_value(
        "CRM Lead",
        {"email": sender_email},
        ["name", "lead_owner", "custom_sales_rm", "custom_service_rm"],
        as_dict=True
    )
    if not lead:
        lead = frappe.db.get_value(
            "CRM Lead",
            {"custom_secondary_email": sender_email},
            ["name", "lead_owner", "custom_sales_rm", "custom_service_rm"],
            as_dict=True
        )

    if lead:
        # Auto-link communication to the Lead document
        if not doc.reference_doctype or not doc.reference_name:
            doc.db_set("reference_doctype", "CRM Lead")
            doc.db_set("reference_name", lead.name)

        # Determine RM user ID
        rm_user = lead.lead_owner
        if not rm_user and lead.custom_service_rm:
            rm_user = frappe.db.get_value("Employee", lead.custom_service_rm, "user_id")
        if not rm_user and lead.custom_sales_rm:
            rm_user = frappe.db.get_value("Employee", lead.custom_sales_rm, "user_id")

        if rm_user:
            frappe.share.add("Communication", doc.name, rm_user, read=1, write=1)


@frappe.whitelist()
def get_email_hub_data():
    user = frappe.session.user
    roles = frappe.get_roles(user)

    if user in ["Administrator", "administrator"] or "System Manager" in roles:
        communications = frappe.db.get_all(
            "Communication",
            fields=["name", "subject", "sender", "recipients", "content", "communication_date", "sent_or_received", "status", "creation", "reference_doctype", "reference_name"],
            order_by="creation desc",
            limit=100
        )
    else:
        # Fetch communications linked to leads owned by this RM or sent/received by this RM
        user_leads = frappe.db.get_all("CRM Lead", filters={"lead_owner": user}, pluck="name")

        conds = ["sender = %(user)s", "recipients LIKE %(user_pattern)s"]
        params = {"user": user, "user_pattern": f"%{user}%"}

        if user_leads:
            conds.append("(reference_doctype = 'CRM Lead' AND reference_name IN %(user_leads)s)")
            params["user_leads"] = user_leads

        where_clause = " OR ".join(conds)
        query = f"""
            SELECT name, subject, sender, recipients, content, communication_date, sent_or_received, status, creation, reference_doctype, reference_name
            FROM `tabCommunication`
            WHERE {where_clause}
            ORDER BY creation DESC
            LIMIT 100
        """
        communications = frappe.db.sql(query, params, as_dict=True)

    failed_emails = frappe.db.get_all(
        "Email Queue",
        filters={"status": ["in", ["Error", "Failed"]]},
        fields=["name", "sender", "message", "error", "status", "creation", "modified"],
        order_by="creation desc",
        limit=50
    )

    for fe in failed_emails:
        recipients = frappe.db.get_all(
            "Email Queue Recipient",
            filters={"parent": fe.name},
            pluck="recipient"
        )
        fe["recipients"] = ", ".join(recipients) if recipients else ""
        fe["subject"] = _("(Failed Email Delivery)")
        fe["content"] = fe.get("message") or fe.get("error") or ""
        fe["sent_or_received"] = "Failed"

    return {
        "communications": communications,
        "failed_emails": failed_emails
    }


@frappe.whitelist(allow_guest=True)
def get_user_info():
    if frappe.session.user == "Guest":
        return {}
    return {
        "name": frappe.session.user,
        "full_name": frappe.utils.get_fullname(frappe.session.user),
        "roles": frappe.get_roles(frappe.session.user)
    }

@frappe.whitelist(allow_guest=True)
def boot_config(*args, **kwargs):
    return {}

@frappe.whitelist(allow_guest=True)
def get_single_value(doctype, field):
    if doctype == "FCRM Settings" and field == "persona_captured":
        val = frappe.db.get_value("Singles", {"doctype": doctype, "field": field}, "value")
        return int(val) if val is not None else 0

    from frappe.client import get_single_value as original_get_single_value
    return original_get_single_value(doctype, field)


