import frappe
from frappe.query_builder import Order
from crm.api.notifications import get_hash

@frappe.whitelist()
def get_notifications():
	# Flush cached app_hooks in Redis so new override_whitelisted_methods are immediately picked up
	try:
		if hasattr(frappe, "client_cache") and frappe.client_cache:
			frappe.client_cache.delete_value("app_hooks")
		frappe.cache().delete_value("app_hooks")
	except Exception:
		pass

	Notification = frappe.qb.DocType("CRM Notification")
	query = (
		frappe.qb.from_(Notification)
		.select("*")
		.where(Notification.to_user == frappe.session.user)
		.orderby("creation", order=Order.desc)
	)
	notifications = query.run(as_dict=True)

	_notifications = []
	for notification in notifications:
		_notifications.append(
			{
				"creation": notification.creation,
				"from_user": {
					"name": notification.from_user,
					"full_name": frappe.get_value("User", notification.from_user, "full_name"),
				},
				"type": notification.type,
				"to_user": notification.to_user,
				"read": notification.read,
				"hash": get_hash(notification),
				"notification_text": notification.notification_text,
				"notification_type_doctype": notification.notification_type_doctype,
				"notification_type_doc": notification.notification_type_doc,
				"reference_doctype": ("deal" if notification.reference_doctype == "CRM Deal" else ("task" if notification.reference_doctype == "CRM Task" else "lead")),
				"reference_name": notification.reference_name,
				"route_name": ("Deal" if notification.reference_doctype == "CRM Deal" else ("Tasks" if notification.reference_doctype == "CRM Task" else "Lead")),
			}
		)

	return _notifications
