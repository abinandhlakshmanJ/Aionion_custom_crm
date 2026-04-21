frappe.provide("aionion_custom");

frappe.ui.form.on("CRM Lead", {
    refresh: function(frm) {
        if (frm.doc.custom_entity !== "Aionion Insurance") return;

        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__("Submit Lead"), function() {
                aionion_custom.submit_lead(frm);
            }).addClass("btn-primary");
        }

        if (frm.doc.docstatus === 1 && frappe.user.has_role("Insurance MIS")) {
            if (frm.doc.custom_mis_status !== "Verified") {
                frm.add_custom_button(__("Verify MIS"), function() {
                    aionion_custom.verify_mis(frm);
                }, __("MIS Actions"));
            }
            if (frm.doc.custom_mis_status !== "Rejected") {
                frm.add_custom_button(__("Reject MIS"), function() {
                    aionion_custom.reject_mis(frm);
                }, __("MIS Actions"));
            }
        }

        if (frm.doc.custom_entity === "Aionion Insurance") {
            const colors = { "Pending": "orange", "Verified": "green", "Rejected": "red" };
            const status = frm.doc.custom_mis_status || "Pending";
            frm.dashboard.add_indicator(__("MIS: {0}", [status]), colors[status] || "grey");
        }
    }
});

aionion_custom.submit_lead = function(frm) {
    if (!frm.doc.custom_policy_status) {
        frappe.msgprint({ title: __("Missing Policy Status"), message: __("Please set Policy Status before submitting."), indicator: "red" });
        return;
    }
    if (frm.doc.custom_policy_status === "Issued" && !frm.doc.custom_policy_number) {
        frappe.msgprint({ title: __("Missing Policy Number"), message: __("Policy Number is mandatory when Policy Status is Issued."), indicator: "red" });
        return;
    }
    frappe.confirm(
        __("Are you sure you want to submit this lead? It will be locked after submission."),
        function() {
            frappe.call({
                method: "aionion_custom.aionion_custom.controllers.crm_lead.submit_insurance_lead",
                args: { lead_name: frm.doc.name },
                freeze: true,
                freeze_message: __("Submitting lead..."),
                callback: function(r) {
                    if (!r.exc) {
                        frappe.msgprint({ title: __("Lead Submitted"), message: __("Lead submitted! MIS team will now verify."), indicator: "green" });
                        frm.reload_doc();
                    }
                }
            });
        }
    );
};

aionion_custom.verify_mis = function(frm) {
    frappe.confirm(
        __("Have you verified Policy No {0} in the insurer portal?", [frm.doc.custom_policy_number || "N/A"]),
        function() {
            frappe.call({
                method: "aionion_custom.aionion_custom.controllers.crm_lead.approve_mis",
                args: { lead_name: frm.doc.name },
                callback: function(r) { if (!r.exc) frm.reload_doc(); }
            });
        }
    );
};

aionion_custom.reject_mis = function(frm) {
    frappe.call({
        method: "aionion_custom.aionion_custom.controllers.crm_lead.reject_mis",
        args: { lead_name: frm.doc.name },
        callback: function(r) { if (!r.exc) frm.reload_doc(); }
    });
};
