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
        "before_validate": [
            "aionion_custom.aionion_custom.controllers.crm_lead.set_sales_rm_defaults"
        ],
        "before_save": [
            "aionion_custom.aionion_custom.controllers.crm_lead.clear_service_rm_on_product_change",
            "aionion_custom.aionion_custom.controllers.crm_lead.set_business_type",
            "aionion_custom.aionion_custom.controllers.crm_lead.sync_lead_owner",
        ],
        "on_submit": [
            "aionion_custom.aionion_custom.controllers.crm_lead.share_lead_with_mis_team",
        ],
        "on_update": [
            "aionion_custom.aionion_custom.controllers.crm_lead.sync_us_subscription_from_lead"
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
    {"dt": "Custom Field", "filters": [["dt", "in", ["CRM Lead", "Customer", "US Subscription Record"]]]},
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
            "US Subscription List Actions",
            "Forecasting Script",
            "US Subscription Actions",
            "Renewals Manager View",
            "Go to Customer from CRM Leads",
            "Product Details Script for CRM Deal",
            "Product Details Script for CRM Lead",
            "Create Task against Lead"
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
            "CRM Lead Import Export",
            "call_log_dashboard",
            "Lead condition",
            "Show only current user in Sales RM",
            "Customer Cross Sell",
            "Button to generate tasks against Leads",
            "Button to start Demat Verification",
            "Create Task for Customer",
            "Display Task Status options as per Product",
            "Aionion Task - Navigate to CRM Leads",
            "US subscription Auto Fetch",
            "US Subscription Record Payment Actions"
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
            "Capital Manager",
            "Global RM",
            "Global RM Manager",
            "US Subscription RM",
            "US Subscription MIS",
            "US Subscription Admin",
            "US Subscription TL",
            "SME Insurance RM",
            "SME Insurance Manager"
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
        "aionion_custom.aionion_custom.tasks.techexcel_sync.sync_customers_from_s3",
    ],
}