frappe.pages['crm-io'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'CRM Import Export',
		single_column: true
	});
}