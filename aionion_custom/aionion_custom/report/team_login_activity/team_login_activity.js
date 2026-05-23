frappe.query_reports["Team Login Activity"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "top_level_manager",
			label: __("Top Level Manager"),
			fieldtype: "Link",
			options: "Employee",
			get_query: function () {
				return {
					filters: { status: "Active" },
				};
			},
		},
	],
};
