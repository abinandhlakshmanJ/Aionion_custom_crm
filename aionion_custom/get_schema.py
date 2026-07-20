import frappe
def execute():
    try:
        print(frappe.db.get_table_columns("CRM View Settings"))
    except Exception as e:
        print(e)
