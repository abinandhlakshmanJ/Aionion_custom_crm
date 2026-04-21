# Copyright (c) 2026, developers@buildwithhussain.com and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class AionionTask(Document):
	pass

def get_data():
    return {
        "fieldname": "aionion_task",

        "links": [
            {
                "link_doctype": "Customer",
                "link_fieldname": "customer"
            },
            {
                "link_doctype": "Project",
                "link_fieldname": "project"
            }
        ]
    }