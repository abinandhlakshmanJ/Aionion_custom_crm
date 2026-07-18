import frappe

def execute():
    data = {
        "name":"Create Customer Onboarding",
        "owner":"shivam@buildwithhussain.tech",
        "creation":"2026-03-12 22:28:22.030532",
        "modified":"2026-03-24 12:09:47.858335",
        "modified_by":"shivam@buildwithhussain.tech",
        "docstatus":0,
        "idx":0,
        "script_type":"API",
        "event_frequency":"All",
        "doctype_event":"Before Insert",
        "api_method":"create_aionion_task",
        "allow_guest":0,
        "disabled":0,
        "script":"lead = frappe.form_dict.get('lead')\naionion_product = frappe.form_dict.get('aionion_product')\n\nlead_doc = frappe.get_doc('CRM Lead', lead)\n\ntask = frappe.new_doc('Aionion Task')\n\nif aionion_product == 'Equity' or aionion_product == 'Bonds' or aionion_product == 'Mutual Funds':\n    task.company = 'Aionion Capital Market Services Private Limited'\nelif aionion_product == 'US Subscription':\n    task.company = 'Aionion Businesses and Management Services LLC'\nelif aionion_product == 'Insurance':\n    task.company = 'Aionion Insurance Marketing Private Limited'\n\nif lead_doc.custom_is_existing_customer == True:\n    task.is_existing_customer = True\n    task.customer = lead_doc.custom_customer\n    cstm = frappe.get_doc('Customer', lead_doc.custom_customer)\n    if cstm.pan and aionion_product == 'US Subscription':\n        task.pan = cstm.pan\n    \ntask.lead = lead_doc.name\ntask.product = aionion_product\ntask.client_name = lead_doc.lead_name\ntask.client_email = lead_doc.email\ntask.mobile_no = lead_doc.mobile_no\ntask.primary_address = lead_doc.custom_address_line_1\ntask.state = lead_doc.custom_state\ntask.city = lead_doc.custom_city\ntask.country = lead_doc.custom_country\ntask.alternate_mobile = lead_doc.custom_alternate_mobile\ntask.rm_employee_code = lead_doc.custom_lead_owner_emp\ntask.rm_user_id = lead_doc.lead_owner\n\ntask.insert()\n\nfrappe.response['message'] = task.name",
        "enable_rate_limit":0,
        "rate_limit_count":5,
        "rate_limit_seconds":86400,
        "doctype":"Server Script"
    }

    if not frappe.db.exists("Server Script", {"name": data["name"]}):
        doc = frappe.get_doc(data)
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print("Successfully inserted Server Script:", data["name"])
    else:
        print("Server Script already exists:", data["name"])
