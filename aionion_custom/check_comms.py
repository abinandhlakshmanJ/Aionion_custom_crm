import frappe

def create_sent_email(recipients, subject, content, sender=None):
    if not sender:
        sender = frappe.session.user
    doc = frappe.get_doc({
        "doctype": "Communication",
        "communication_type": "Communication",
        "communication_medium": "Email",
        "sent_or_received": "Sent",
        "sender": sender,
        "recipients": recipients,
        "subject": subject,
        "content": content,
        "status": "Linked",
    })
    doc.insert(ignore_permissions=True)
    return doc.name

def execute():
    name = create_sent_email("abinandhlakshman20@gmail.com", "Test Email Subject", "Hello from CRM")
    print(f"Created Communication: {name}")
