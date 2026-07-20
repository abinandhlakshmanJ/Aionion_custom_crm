import frappe
def execute():
    try:
        custom_field = frappe.db.get_value("Custom Field", {"dt": "CRM Lead", "fieldname": "business_type"}, ["in_standard_filter", "in_list_view"], as_dict=1)
        print(f"Custom Field settings: {custom_field}")
        
        # Also check property setters for standard fields
        prop_setters = frappe.db.get_all("Property Setter", {"doc_type": "CRM Lead", "property": "in_standard_filter", "value": "1"}, ["field_name"])
        print(f"Property Setters for in_standard_filter: {prop_setters}")
    except Exception as e:
        print(e)
