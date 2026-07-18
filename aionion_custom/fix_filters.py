import frappe

def execute():
    scripts = frappe.db.get_all("CRM Form Script", filters={"script": ["like", "%setFilters%"]}, fields=["name", "script"])
    
    count = 0
    for doc in scripts:
        script_content = doc.script
        
        # Replace the function signature
        script_content = script_content.replace("{ call, columns, filters, setFilters }", "{ call, list }")
        
        # Replace the setFilters for Lead Hierarchy
        if "lead_owner" in script_content:
            script_content = script_content.replace(
                'setFilters([\n                { fieldname: "lead_owner", operator: "in", value: userIds }\n            ])',
                'let curFilters = list.params.filters || {};\n            curFilters["lead_owner"] = ["in", userIds];\n            list.update({ filters: curFilters });\n            list.reload();'
            )
            # Fallback for single line
            script_content = script_content.replace(
                'setFilters([{ fieldname: "lead_owner", operator: "in", value: userIds }])',
                'let curFilters = list.params.filters || {};\n            curFilters["lead_owner"] = ["in", userIds];\n            list.update({ filters: curFilters });\n            list.reload();'
            )

        # Replace the setFilters for Renewals Manager
        if "custom_product" in script_content:
            script_content = script_content.replace(
                'setFilters([\n                { fieldname: "custom_product", operator: "=", value: "Insurance Renewals" }\n            ])',
                'let curFilters = list.params.filters || {};\n            curFilters["custom_product"] = ["=", "Insurance Renewals"];\n            list.update({ filters: curFilters });\n            list.reload();'
            )
            
        frappe.db.set_value("CRM Form Script", doc.name, "script", script_content)
        count += 1
        
    frappe.db.commit()
    print(f"Fixed {count} CRM Form Scripts.")
