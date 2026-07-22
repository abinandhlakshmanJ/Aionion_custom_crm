import frappe


def execute():
    """Add persona_captured column to FCRM Settings if missing."""
    if not frappe.db.has_column("FCRM Settings", "persona_captured"):
        frappe.db.sql("""
            ALTER TABLE `tabFCRM Settings`
            ADD COLUMN `persona_captured` INT(1) NOT NULL DEFAULT 0
        """)
        frappe.db.commit()
