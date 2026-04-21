// Copyright (c) 2026, developers@buildwithhussain.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Insurance Record", {
	refresh(frm) {
		// Task 7 — PRD Section 5.3
		// Show MIS Approve / Reject buttons only for Insurance MIS role users
		// and only on unsaved draft records (docstatus = 0)
		if (frm.doc.docstatus === 0 && frappe.user.has_role("Insurance MIS")) {
			if (frm.doc.custom_mis_status !== "Approved") {
				frm.add_custom_button(__("Approve MIS"), async () => {
					const confirmed = await frappe.confirm(
						__("Are you sure you have verified policy number <b>{0}</b> in the insurer portal?",
							[frm.doc.policy_number || "N/A"])
					);
					if (!confirmed) return;

					frappe.call({
						method: "aionion_custom.aionion_custom.doctype.insurance_record.insurance_record.approve_mis",
						args: { insurance_record_name: frm.doc.name },
						callback(r) {
							if (!r.exc) frm.reload_doc();
						}
					});
				}, __("MIS Actions"));
			}

			if (frm.doc.custom_mis_status !== "Rejected") {
				frm.add_custom_button(__("Reject MIS"), () => {
					frappe.call({
						method: "aionion_custom.aionion_custom.doctype.insurance_record.insurance_record.reject_mis",
						args: { insurance_record_name: frm.doc.name },
						callback(r) {
							if (!r.exc) frm.reload_doc();
						}
					});
				}, __("MIS Actions"));
			}
		}

		// Visual indicator for MIS status
		const statusColors = {
			"Pending": "orange",
			"Approved": "green",
			"Rejected": "red"
		};
		const misStatus = frm.doc.custom_mis_status || "Pending";
		const color = statusColors[misStatus] || "grey";
		frm.dashboard.add_indicator(__("MIS: {0}", [misStatus]), color);
	},
});
