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
// ── US Subscription Buttons ──────────────────────────────────────────────────

frappe.ui.form.on("CRM Lead", {
    refresh: function(frm) {
        if (frm.doc.custom_entity !== "US Subscription") return;

        // Submit button — for Sales RM
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__("Submit US Lead"), function() {
                aionion_custom.submit_us_lead(frm);
            }).addClass("btn-primary");
        }

        // MIS buttons — for US Subscription MIS
        if (frm.doc.docstatus === 1 && frappe.user.has_role("US Subscription MIS")) {
            if (frm.doc.custom_mis_status !== "Approved") {
                frm.add_custom_button(__("Verify Payment"), function() {
                    aionion_custom.verify_us_payment(frm);
                }, __("MIS Actions"));
            }
            if (frm.doc.custom_mis_status !== "Rejected") {
                frm.add_custom_button(__("Reject Payment"), function() {
                    aionion_custom.reject_us_payment(frm);
                }, __("MIS Actions"));
            }
        }

        // Status indicator
        const colors = { "Pending": "orange", "Approved": "green", "Rejected": "red" };
        const status = frm.doc.custom_mis_status || "Pending";
        frm.dashboard.add_indicator(__("Payment: {0}", [status]), colors[status] || "grey");
    }
});

aionion_custom.submit_us_lead = function(frm) {
    // Validate mandatory fields before submit
    let mandatory = {
        "lead_name": "Client Name",
        "mobile_no": "Contact Number",
        "email": "Email",
        "custom_country": "Country of Residence",
        "custom_employee_status": "Employment Status",
        "custom_client_indian_investments": "Indian Investments",
        "custom_client_intended_investment_in_us_market": "Intended Investment",
        "custom_aionion_client_code": "Aionion Client Code",
        "custom_sales_rm_code": "EMP Code",
        "custom_lead_owner_name": "EMP Name",
        "custom_sales_rm_team": "EMP Team",
        "custom_sales_rm_branch": "EMP Branch",
    };

    let missing = [];
    for (let [field, label] of Object.entries(mandatory)) {
        if (!frm.doc[field]) missing.push(label);
    }

    if (missing.length) {
        frappe.msgprint({
            title: __("Missing Mandatory Fields"),
            message: __("Please fill the following fields before submitting:<br><br><b>{0}</b>", [missing.join("<br>")]),
            indicator: "red"
        });
        return;
    }

    frappe.confirm(
        __("Are you sure you want to submit this US Subscription lead for payment verification?"),
        function() {
            frappe.call({
                method: "aionion_custom.aionion_custom.controllers.crm_lead.submit_us_lead",
                args: { lead_name: frm.doc.name },
                freeze: true,
                freeze_message: __("Submitting lead..."),
                callback: function(r) {
                    if (!r.exc) {
                        frappe.msgprint({
                            title: __("Lead Submitted"),
                            message: __("US Lead submitted! MIS team will now verify payment."),
                            indicator: "green"
                        });
                        frm.reload_doc();
                    }
                }
            });
        }
    );
};

aionion_custom.verify_us_payment = function(frm) {
    frappe.confirm(
        __("Have you verified the payment for {0}?", [frm.doc.lead_name]),
        function() {
            frappe.call({
                method: "aionion_custom.aionion_custom.controllers.crm_lead.verify_us_payment",
                args: { lead_name: frm.doc.name },
                freeze: true,
                freeze_message: __("Verifying payment..."),
                callback: function(r) {
                    if (!r.exc) {
                        frappe.msgprint({
                            title: __("Payment Verified"),
                            message: __("Payment verified! Customer and US Subscription Record are being created."),
                            indicator: "green"
                        });
                        frm.reload_doc();
                    }
                }
            });
        }
    );
};

aionion_custom.reject_us_payment = function(frm) {
    let d = new frappe.ui.Dialog({
        title: __("Reject Payment"),
        fields: [{
            fieldname: "reason",
            fieldtype: "Small Text",
            label: __("Reason for Rejection"),
            reqd: 1
        }],
        primary_action_label: __("Reject"),
        primary_action(values) {
            frappe.call({
                method: "aionion_custom.aionion_custom.controllers.crm_lead.reject_us_payment",
                args: { lead_name: frm.doc.name, reason: values.reason },
                callback: function(r) {
                    if (!r.exc) {
                        frappe.msgprint({
                            title: __("Payment Rejected"),
                            message: __("Payment rejected. Lead owner has been notified."),
                            indicator: "red"
                        });
                        frm.reload_doc();
                    }
                }
            });
            d.hide();
        }
    });
    d.show();
};