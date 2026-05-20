frappe.query_reports["US CRM Details Report"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("Data Entry From"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
        },
        {
            fieldname: "to_date",
            label: __("Data Entry To"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
        },
        {
            fieldname: "payment_from_date",
            label: __("Payment From Date"),
            fieldtype: "Date",
        },
        {
            fieldname: "payment_to_date",
            label: __("Payment To Date"),
            fieldtype: "Date",
        },
        {
            fieldname: "client_status_new",
            label: __("Client Status"),
            fieldtype: "Select",
            options: "\nNew\nRNL",
        },
        {
            fieldname: "subscription_type_new",
            label: __("Subscription Type"),
            fieldtype: "Select",
            options: "\nAnnual\nTwo Years\nThree Years",
        },
        {
            fieldname: "mode_of_payment_new",
            label: __("Mode of Payment"),
            fieldtype: "Select",
            options: "\nPayment Gateway\nBank Transfer",
        },
        {
            fieldname: "currency_new",
            label: __("Currency"),
            fieldtype: "Select",
            options: "\nUSD\nAED",
        },
        {
            fieldname: "sales_done_by",
            label: __("Sales Done By"),
            fieldtype: "Link",
            options: "Employee",
        },
        {
            fieldname: "team",
            label: __("Team"),
            fieldtype: "Select",
            options: "\nChennai\nDubai\nMadurai",
        },
        {
            fieldname: "lead_source",
            label: __("Lead Source"),
            fieldtype: "Link",
            options: "Lead Source",
        },
        {
            fieldname: "country_of_residence",
            label: __("Country of Residence"),
            fieldtype: "Link",
            options: "Country",
        },
        {
            fieldname: "email_sent",
            label: __("Acknowledgment Sent"),
            fieldtype: "Select",
            options: "\nYes\nNo",
        },
    ],
};