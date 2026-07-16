__version__ = "0.0.1"


def _apply_crm_patches():
    """
    Runtime monkey-patches for Frappe CRM compatibility.

    These patches replicate changes that were previously made directly to core
    CRM files. By keeping them here, the core `crm` app stays 100% stock and
    can be updated freely without losing our customisations.

    Patch 1 – Bypass linked-doc check in crm/api/doc.py
    -------------------------------------------------------
    The original code imported get_linked_docs / get_dynamic_linked_docs from
    frappe.model.delete_doc.  That import broke on Frappe v16 and the
    resulting slow query made bulk-deletes hang.  We replace both functions
    with fast no-ops so CRM delete still works instantly.

    Patch 2 – Fix assign_to import in crm_lead.py and crm_deal.py
    ---------------------------------------------------------------
    Frappe v16 renamed frappe.desk.form.assign_to._add → add.
    The stock CRM still calls _add, so we add the alias back if it is missing.
    """
    try:
        # ── Patch 1 ──────────────────────────────────────────────────────────
        import crm.api.doc as _crm_doc

        _crm_doc.get_linked_docs = lambda doc: []
        _crm_doc.get_dynamic_linked_docs = lambda doc: []

    except ImportError:
        pass  # CRM app not installed — skip silently

    try:
        # ── Patch 2 ──────────────────────────────────────────────────────────
        import frappe.desk.form.assign_to as _assign_to

        if hasattr(_assign_to, "add") and not hasattr(_assign_to, "_add"):
            _assign_to._add = _assign_to.add

    except ImportError:
        pass  # Frappe not available in this context — skip silently


_apply_crm_patches()
