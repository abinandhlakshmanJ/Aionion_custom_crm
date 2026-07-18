import frappe

def execute():
    # Check Client Script
    client_scripts = frappe.db.sql("select name, script from `tabClient Script` where script like '%setFilters%'", as_dict=True)
    if client_scripts:
        print("Found in Client Script:")
        for cs in client_scripts:
            print("=================")
            print(cs.name)
            print("=================")
            print(cs.script)
        
    # Check CRM Form Script
    if frappe.db.exists("DocType", "CRM Form Script"):
        form_scripts = frappe.db.sql("select name, script from `tabCRM Form Script` where script like '%setFilters%'", as_dict=True)
        if form_scripts:
            print("Found in CRM Form Script:")
            for fs in form_scripts:
                print("=================")
                print(fs.name)
                print("=================")
                print(fs.script)
