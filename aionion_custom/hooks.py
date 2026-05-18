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
    },
}

# Fixtures
# --------
fixtures = [
    "Insurance Company",
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
            "Insurance Renewal Record — MIS Actions"
        ]]]
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
            "Global RM",
            "US Subscription RM",
            "US Subscription MIS",
            "US Subscription Admin"
        ]]]
    },
]

# Scheduled Tasks
# ---------------
scheduler_events = {
    "cron": {
        "*/2 * * * *": [
            "frappe.email.doctype.email_account.email_account.pull",
        ],
    },
    "daily": [
        "aionion_custom.aionion_custom.controllers.crm_lead.send_us_subscription_expiry_notifications",
    ],
}