frappe.query_reports["US CRM Details Report"] = {
    filters: [
        {fieldname:"from_date",label:__("From Date"),fieldtype:"Date",default:frappe.datetime.add_months(frappe.datetime.get_today(),-1)},
        {fieldname:"to_date",label:__("To Date"),fieldtype:"Date",default:frappe.datetime.get_today()},
        {fieldname:"payment_status",label:__("Payment Status"),fieldtype:"Select",options:"\nPending\nApproved\nRejected"},
        {fieldname:"client_status_new",label:__("Client Status"),fieldtype:"Select",options:"\nNew\nRNL"},
        {fieldname:"subscription_type_new",label:__("Subscription Type"),fieldtype:"Select",options:"\nAnnual\nTwo Years\nThree Years"},
        {fieldname:"team",label:__("Team"),fieldtype:"Select",options:"\nChennai\nDubai\nMadurai"},
        {fieldname:"sales_done_by",label:__("Sales Done By"),fieldtype:"Link",options:"Employee"},
    ],
};
