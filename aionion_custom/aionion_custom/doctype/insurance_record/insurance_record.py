# Copyright (c) 2026, developers@buildwithhussain.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today


class InsuranceRecord(Document):

    def validate(self):
        """
        Task 8 — PRD Section 5.4
        Server-side validation rules enforced on every save attempt.

        WHY here and not in JS:
        - JS can be bypassed via API. Server-side is the only reliable enforcement.
        - frappe.throw() surfaces a user-friendly error in the UI as a red banner.
        """
        self._validate_policy_number()
        self._validate_renewal_fields()

    def on_submit(self):
        """
        Task 8 — PRD Section 5.4
        Final gate before the Insurance Record is locked (docstatus = 1).
        MIS must be Approved before any submission can proceed.
        """
        self._block_if_mis_not_approved()

    def _validate_policy_number(self):
        """
        PRD rule: policy_number is mandatory ONLY when status = Issued.
        If Rejected → submission allowed without policy number.
        """
        if self.policy_status == "Issued" and not self.policy_number:
            frappe.throw(
                _("Policy Number is mandatory for Issued policies."),
                title=_("Missing Policy Number")
            )

    def _validate_renewal_fields(self):
        """
        PRD 9.3.4: When status = Renewed, both new policy_number
        and custom_new_expiry_date are mandatory.
        """
        if self.policy_status == "Renewed":
            if not self.policy_number:
                frappe.throw(
                    _("New Policy Number is mandatory for Renewed status."),
                    title=_("Missing Policy Number")
                )
            if not self.custom_new_expiry_date:
                frappe.throw(
                    _("New Expiry Date is mandatory for Renewed status."),
                    title=_("Missing Expiry Date")
                )

    def _block_if_mis_not_approved(self):
        """
        PRD rule: Lead cannot be submitted until MIS Status = Approved.
        We enforce this on Insurance Record submit — the CRM Lead on_submit
        will also re-check this as a pre-condition (defence in depth).
        """
        if self.custom_mis_status != "Approved":
            frappe.throw(
                _("MIS verification must be Approved before submitting this Insurance Record. "
                  "Current MIS Status: {0}").format(self.custom_mis_status or "Pending"),
                title=_("MIS Verification Required")
            )


@frappe.whitelist()
def approve_mis(insurance_record_name):
    """
    Task 7 — PRD Section 5.3
    Called by MIS team to approve the Insurance Record after portal verification.

    WHY a whitelisted method and not direct field edit:
    - We need to stamp mis_verified_by and mis_verified_date automatically.
    - We use ignore_permissions=True here because MIS team needs write access
      only to the MIS status fields, not the full document. This is the minimal
      surface approach — the method itself enforces the MIS role check.

    Role check: only users with 'Insurance MIS' role can call this.
    """
    _check_mis_role()

    doc = frappe.get_doc("Insurance Record", insurance_record_name)

    if doc.docstatus == 1:
        frappe.throw(_("Cannot update MIS status on a submitted Insurance Record."))

    doc.custom_mis_status = "Approved"
    doc.custom_mis_verified_by = frappe.session.user
    doc.custom_mis_verified_date = today()

    # ignore_permissions justified: MIS team has targeted write access via this
    # method only — they cannot edit any other fields directly.
    doc.save(ignore_permissions=True)

    frappe.msgprint(
        _("MIS Status set to Approved for {0}").format(insurance_record_name),
        indicator="green"
    )
    return "Approved"


@frappe.whitelist()
def reject_mis(insurance_record_name, reason=None):
    """
    Task 7 — PRD Section 5.3
    Called by MIS team to reject. Service RM will need to re-check portal
    and either re-submit or amend.
    """
    _check_mis_role()

    doc = frappe.get_doc("Insurance Record", insurance_record_name)

    if doc.docstatus == 1:
        frappe.throw(_("Cannot update MIS status on a submitted Insurance Record."))

    doc.custom_mis_status = "Rejected"
    doc.custom_mis_verified_by = frappe.session.user
    doc.custom_mis_verified_date = today()
    doc.save(ignore_permissions=True)

    frappe.msgprint(
        _("MIS Status set to Rejected for {0}").format(insurance_record_name),
        indicator="red"
    )
    return "Rejected"


def _check_mis_role():
    """
    Enforce that only Insurance MIS role users can approve/reject.
    Raises PermissionError if the current user doesn't have the role.
    """
    if not frappe.has_role("Insurance MIS"):
        frappe.throw(
            _("Only users with the 'Insurance MIS' role can approve or reject MIS status."),
            frappe.PermissionError
        )
