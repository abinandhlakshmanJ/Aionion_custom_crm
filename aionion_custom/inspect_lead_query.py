import frappe
from frappe.model.utils.user_settings import get_user_settings

def execute():
    us = get_user_settings("CRM Lead")
    print("=== GET USER SETTINGS FOR CRM Lead ===")
    print(us)
