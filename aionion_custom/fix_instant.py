import frappe

def execute():
    # check if cron_format field exists
    if frappe.db.exists("DocField", {"parent": "Server Script", "fieldname": "cron_format"}):
        frappe.db.set_value("Server Script", "Scheduler Event For CRM Task", "event_frequency", "Cron")
        frappe.db.set_value("Server Script", "Scheduler Event For CRM Task", "cron_format", "* * * * *")
        print("Updated to Cron (every minute)")
    else:
        frappe.db.set_value("Server Script", "Scheduler Event For CRM Task", "event_frequency", "All")
        print("Updated to All (every 3-4 mins)")
        
    frappe.db.commit()
