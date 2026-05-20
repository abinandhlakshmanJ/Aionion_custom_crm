app_name = "aionion_custom"
app_title = "Aionion Custom"
app_publisher = "developers@buildwithhussain.com"
app_description = "Custom App for Aionion"
app_email = "developers@buildwithhussain.com"
app_license = "mit"

# Includes in <head>
# ------------------
# app_include_css = "/assets/aionion_custom/css/aionion_custom.css"
# app_include_js = ["/assets/aionion_custom/js/crm_mail_inbox_btn.js"]
app_include_css = ["/assets/aionion_custom/css/crm_custom.css"]
# web_include_css = "/assets/aionion_custom/css/aionion_custom.css"
# web_include_js = "/assets/aionion_custom/js/aionion_custom.js"

# Permissions
# -----------
permission_query_conditions = {
    "CRM Lead": "aionion_custom.aionion_custom.controllers.crm_lead.get_permission_query_conditions",
}

# Document Events
# ---------------
doc_events = {
    "CRM Lead": {
        "before_save": [
            "aionion_custom.aionion_custom.controllers.crm_lead.set_sales_rm_defaults",
            "aionion_custom.aionion_custom.controllers.crm_lead.set_business_type",
            "aionion_custom.aionion_custom.controllers.crm_lead.sync_lead_owner",
        ],
        "on_submit": [
            "aionion_custom.aionion_custom.controllers.crm_lead.share_lead_with_mis_team",
        ],
        "validate": [
            "aionion_custom.aionion_custom.controllers.crm_lead.validate_lead_owner_change",
        ],
    },
    "ToDo": {
        "before_insert": [
            "aionion_custom.aionion_custom.controllers.crm_lead.validate_crm_lead_assignment",
        ],
    },
}

# Fixtures
# --------
fixtures = [
    "Insurance Company",
    {"dt": "Custom Field", "filters": [["name", "in", ["CRM Lead-custom_product"]]]},
    "CRM Lead Source",
    {
        "dt": "CRM Form Script",
        "filters": [["name", "in", [
            "CRM Lead Submit",
            "Insurance MIS Actions",
            "Customer Actions",
            "Customer Call Button",
            "Navigate to Customers and Aionion Tasks",
            "Lead Hierarchy Filter",
            "US Subscription List Actions"
        ]]]
    },
    {
        "dt": "Client Script",
        "filters": [["name", "in", [
            "Customer 360 View",
            "Create Lead from Customer",
            "Go to CRM Leads from Customer",
            "Call Button for Customer",
            "Insurance Renewal Record — MIS Actions",
            "US subscription Auto Fetch",
            "US Subscription Record Payment Actions"
        ]]]
    },
    {
        "dt": "Custom Field",
        "filters": [["dt", "=", "US Subscription Record"]]
    },
    {
        "dt": "Role",
        "filters": [["role_name", "in", [
            "Insurance Sales RM",
            "Insurance Service RM",
            "Insurance Renewals RM",
            "Insurance Renewals Manager",
            "Insurance MIS",
            "Insurance Sales Manager",
            "Capital RM",
            "Capital Manager",
            "Global RM",
            "Global RM Manager",
            "US Subscription RM",
            "US Subscription MIS",
            "US Subscription Admin"
        ]]]
    },
    {
        "dt": "Property Setter",
        "filters": [["doc_type", "=", "US Subscription Record"]]
    },
]

# Scheduled Tasks
# ---------------
scheduler_events = {
    "cron": {
        "*/2 * * * *": [
            "frappe.email.doctype.email_account.email_account.pull",
        ],
        "0 0 1 1 *": [
            "aionion_custom.aionion_custom.controllers.crm_lead.auto_extend_month_options",
        ],
    },
    "daily": [
        "aionion_custom.aionion_custom.controllers.crm_lead.send_us_subscription_expiry_notifications",
    ],
}