import frappe
import json
import os

def execute():
    file_path = "/home/abinandh/frappe/my-bench/apps/aionion_custom/aionion_custom/raw_server_scripts.txt"
    
    if not os.path.exists(file_path):
        print("Raw scripts file not found.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    success_count = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Find the JSON part (ignore whatsapp prefixes)
        start_idx = line.find('{')
        end_idx = line.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            json_str = line[start_idx:end_idx+1]
            try:
                data = json.loads(json_str)
                name = data.get("name")
                
                if not name:
                    continue
                    
                if not frappe.db.exists("Server Script", {"name": name}):
                    doc = frappe.get_doc(data)
                    doc.insert(ignore_permissions=True)
                    frappe.db.commit()
                    print("Successfully inserted Server Script:", name)
                    success_count += 1
                else:
                    # Update existing script
                    doc = frappe.get_doc("Server Script", name)
                    doc.update(data)
                    doc.save(ignore_permissions=True)
                    frappe.db.commit()
                    print("Updated existing Server Script:", name)
                    success_count += 1
                    
            except Exception as e:
                print(f"Failed to process a line: {e}")
                
    print(f"\nTotal scripts processed: {success_count}")
