import frappe
def execute():
    t = frappe.db.get_value("CRM Task", "11", ["reference_doctype", "reference_docname"], as_dict=True)
    print(t)
    
    n = frappe.db.get_value("CRM Notification", {"reference_name": "11"}, ["name", "reference_doctype", "reference_name"], as_dict=True)
    print(n)
