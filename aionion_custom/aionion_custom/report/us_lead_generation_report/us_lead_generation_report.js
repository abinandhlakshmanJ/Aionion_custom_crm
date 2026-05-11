frappe.query_reports["US Lead Generation Report"] = {
    filters: [
        {fieldname:"from_date",label:__("From Date"),fieldtype:"Date",default:frappe.datetime.add_months(frappe.datetime.get_today(),-1)},
        {fieldname:"to_date",label:__("To Date"),fieldtype:"Date",default:frappe.datetime.get_today()},
        {fieldname:"emp_team",label:__("EMP Team"),fieldtype:"Select",options:"\nChennai\nDubai\nMadurai"},
        {fieldname:"eligibility",label:__("Eligibility"),fieldtype:"Select",options:"\nEligible\nNot Eligible\nAlready Subscribed\nRepeated"},
        {fieldname:"us_status",label:__("Status"),fieldtype:"Select",options:"\nDropped\nIn Process\nNot Eligible\nSubscribed\nReminder Month"},
        {fieldname:"month",label:__("Month"),fieldtype:"Select",options:"\nApril 2026\nMay 2026\nJune 2026\nJuly 2026\nAugust 2026\nSeptember 2026\nOctober 2026\nNovember 2026\nDecember 2026"},
    ],
};
