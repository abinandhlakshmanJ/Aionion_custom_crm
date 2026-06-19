import frappe
from frappe import _
from frappe.utils import today


# ---------------------------------------------------------------------------
# CROSS-SELL LEAD — Insurance & US Subscription only
# ---------------------------------------------------------------------------

@frappe.whitelist()
def create_cross_sell_lead(customer_name, entity, product, insurance_products=None):
	"""
	Creates a cross-sell CRM Lead from a Customer record.
	Only for Insurance and US Subscription entities.

	For Insurance leads, insurance_products (Health/Term/Motor/etc.)
	is passed from the dialog and stored on the lead directly.

	Duplicate guard (checked in order):
	  1. PAN    — customer.custom_pan vs lead.custom_pan_number
	  2. Mobile — customer.custom_mobile vs lead.mobile_no
	  3. Name   — customer.customer_name vs lead.lead_name

	If ANY active lead already exists for that entity + any of the above
	matches → frappe.throw() with the existing lead name.
	Active = any status except Lost and Converted (those are terminal).
	"""
	customer = frappe.get_cached_doc("Customer", customer_name)

	# 1. Duplicate guard — server side, throws before any insert
	# For Insurance: scoped by entity + insurance_products type (Term ≠ Health)
	# For US Subscription: scoped by entity only
	existing = _find_existing_cross_sell_lead(customer, entity, insurance_products)
	if existing:
		# Build a clear message — for Insurance include the type (Term/Health/etc.)
		if insurance_products:
			label = "{0} — {1}".format(entity, insurance_products)
		else:
			label = entity
		frappe.throw(
			_("A cross-sell lead already exists for this customer under {0}: {1}").format(
				label, existing
			),
			title=_("Duplicate Lead")
		)

	# 2. Resolve Sales RM
	# Prefer customer's assigned RM; fall back to current user's Employee
	sales_rm = customer.get("custom_relationship_manager") or frappe.db.get_value(
		"Employee", {"user_id": frappe.session.user}, "name"
	)

	# 3. Build the lead
	business_type_map = {
		"Insurance Sales": "New Business",
		"Insurance Renewals": "Renewal",
	}

	parts = (customer.customer_name or "").split(" ", 1)
	first_name = parts[0]
	last_name = parts[1] if len(parts) > 1 else ""

	lead = frappe.get_doc({
		"doctype": "CRM Lead",
		# Identity
		"first_name": first_name,
		"last_name": last_name,
		"lead_name": customer.customer_name,
		"mobile_no": customer.get("custom_mobile"),
		"email": customer.get("custom_email"),
		# PAN — Customer stores it in `custom_pan` (TechExcel sync field, confirmed)
		# CRM Lead stores it in `custom_pan_number`
		"custom_pan_number": customer.get("custom_pan"),
		# Entity / product
		"custom_entity": entity,
		"custom_product": product,
		"custom_business_type": business_type_map.get(product, "New Business"),
		# Insurance type — passed from dialog for Insurance leads, None for US Subscription
		"custom_insurance_type": insurance_products or None,
		# Customer link — marks this as a cross-sell from an existing customer
		"custom_customer": customer_name,
		"custom_is_existing_customer": 1,
		"custom_client_category": "Aionion Client",
		"custom_aionion_client_code": customer.get("custom_aionion_master_id"),
		# Demographics
		"custom_dob": customer.get("custom_dob"),
		"custom_residency": customer.get("custom_residency") or "Indian",
		# RM assignment
		"custom_sales_rm": sales_rm,
		"custom_service_rm": customer.get("custom_service_rm"),
		"custom_service_rm_name": customer.get("custom_service_rm_name"),
		# Dates & status
		"custom_lead_date": today(),
		"lead_owner": frappe.session.user,
		"status": "New",
	})

	lead.flags.ignore_mandatory = True  # safety net — critical checks done above
	lead.insert(ignore_permissions=True)
	frappe.db.commit()

	return lead.name


def _find_existing_cross_sell_lead(customer, entity, insurance_products=None):
	"""
	Returns the name of an existing active CRM Lead that matches:
	  - same entity (Aionion Insurance / US Subscription)
	  - same insurance type (only for Insurance — Health/Term/Motor etc.)
	  - same customer by PAN, mobile, or name

	For Insurance leads: scoped by BOTH entity AND insurance_products.
	  → One Term lead + one Health lead allowed simultaneously.
	  → Two Term leads blocked.

	For US Subscription: scoped by entity only (no insurance type).

	Uses frappe.qb — no raw SQL.
	"""
	from frappe.query_builder import DocType

	Lead = DocType("CRM Lead")

	# Terminal statuses — a new cross-sell lead is valid after these
	terminal_statuses = ["Lost", "Converted"]

	pan    = customer.get("custom_pan")
	mobile = customer.get("custom_mobile")
	name   = customer.customer_name

	# Nothing to match on — skip check
	if not any([pan, mobile, name]):
		return None

	# Build OR match condition across the three identifiers
	match_condition = None

	if pan:
		match_condition = Lead.custom_pan_number == pan

	if mobile:
		m = Lead.mobile_no == mobile
		match_condition = m if match_condition is None else (match_condition | m)

	if name:
		n = Lead.lead_name == name
		match_condition = n if match_condition is None else (match_condition | n)

	# Base filter: entity + active status + customer identity
	where_clause = (
		(Lead.custom_entity == entity)
		& (Lead.status.notin(terminal_statuses))
		& match_condition
	)

	# For Insurance: also scope by insurance type so Term and Health are independent
	if entity == "Aionion Insurance" and insurance_products:
		where_clause = where_clause & (Lead.custom_insurance_type == insurance_products)

	result = (
		frappe.qb.from_(Lead)
		.select(Lead.name)
		.where(where_clause)
		.limit(1)
		.run(as_dict=True)
	)

	return result[0].name if result else None


# ---------------------------------------------------------------------------
# BONDS PURCHASE RECORD — direct creation from Customer (no lead required)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def create_bonds_record(customer_name):
	"""
	Creates a new Bonds Purchase Record directly linked to the Customer,
	OR returns the existing draft (docstatus=0) if one already exists.

	This prevents duplicate empty records when the user clicks the button
	multiple times without filling in the previous record.

	Returns: { "name": "BONDS-XXX", "is_existing": True/False }
	"""
	# Check for an existing unfilled draft first
	existing_draft = frappe.db.get_value(
		"Bonds Purchase Record",
		{"customer": customer_name, "docstatus": 0},
		"name",
		order_by="creation desc",
	)
	if existing_draft:
		return {"name": existing_draft, "is_existing": True}

	# No draft exists — create a fresh one
	customer = frappe.get_cached_doc("Customer", customer_name)

	sales_rm = customer.get("custom_relationship_manager") or frappe.db.get_value(
		"Employee", {"user_id": frappe.session.user}, "name"
	)

	rm_name = (customer.get("custom_rm_name") or (
		frappe.db.get_value("Employee", sales_rm, "employee_name") if sales_rm else ""
	))

	doc = frappe.get_doc({
		"doctype": "Bonds Purchase Record",
		"customer": customer_name,
		"client_name": customer.customer_name,
		"pan": customer.get("custom_pan"),
		"client_code": customer.get("custom_client_code"),
		"rm_employee_code": sales_rm,
		"rm_employee_name": rm_name,
		"branch": customer.get("custom_branch_code") or None,
		"company": frappe.db.get_single_value("Global Defaults", "default_company") or "",
	})

	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True)
	frappe.db.commit()

	return {"name": doc.name, "is_existing": False}


# ---------------------------------------------------------------------------
# MUTUAL FUNDS RECORD — direct creation from Customer (no lead required)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def create_mf_record(customer_name):
	"""
	Creates a new Mutual Funds Record directly linked to the Customer,
	OR returns the existing draft (docstatus=0) if one already exists.

	This prevents duplicate empty records when the user clicks the button
	multiple times without filling in the previous record.

	Returns: { "name": "MF-XXX", "is_existing": True/False }
	"""
	# Check for an existing unfilled draft first
	existing_draft = frappe.db.get_value(
		"Mutual Funds Record",
		{"customer": customer_name, "docstatus": 0},
		"name",
		order_by="creation desc",
	)
	if existing_draft:
		return {"name": existing_draft, "is_existing": True}

	# No draft exists — create a fresh one
	customer = frappe.get_cached_doc("Customer", customer_name)

	sales_rm = customer.get("custom_relationship_manager") or frappe.db.get_value(
		"Employee", {"user_id": frappe.session.user}, "name"
	)

	rm_name = (customer.get("custom_rm_name") or (
		frappe.db.get_value("Employee", sales_rm, "employee_name") if sales_rm else ""
	))

	doc = frappe.get_doc({
		"doctype": "Mutual Funds Record",
		"customer": customer_name,
		"client_name": customer.customer_name,
		"pan": customer.get("custom_pan"),
		"client_code": customer.get("custom_client_code"),
		"rm_employee_code": sales_rm,
		"rm_employee_name": rm_name,
		"sales_done_by": sales_rm,
		"branch": customer.get("custom_branch_code") or None,
		"company": frappe.db.get_single_value("Global Defaults", "default_company") or "",
	})

	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True)
	frappe.db.commit()

	return {"name": doc.name, "is_existing": False}


# ---------------------------------------------------------------------------
# INSURANCE RECORD — direct creation from Customer, scoped by insurance type
# ---------------------------------------------------------------------------

@frappe.whitelist()
def create_insurance_record(customer_name, insurance_products):
	"""
	Creates a new Insurance Record directly linked to the Customer,
	OR returns the existing draft (docstatus=0) for that specific
	insurance_products type if one already exists.

	Duplicate rule: ONE draft per customer per insurance_products type.
	  - Customer can have a Health draft AND a Term draft simultaneously.
	  - But NOT two Health drafts — clicking again opens the existing one.

	Args:
	  customer_name     : Customer.name
	  insurance_products: the insurance type selected in the dialog
	                      (Health / Term / Motor / Travel / SME / etc.)

	Returns: { "name": "INS-XXX", "is_existing": True/False }
	"""
	# Check for existing draft of same type for this customer
	existing_draft = frappe.db.get_value(
		"Insurance Record",
		{
			"customer": customer_name,
			"insurance_products": insurance_products,
			"docstatus": 0,
		},
		"name",
		order_by="creation desc",
	)
	if existing_draft:
		return {"name": existing_draft, "is_existing": True}

	# No draft of this type exists — create a fresh one
	customer = frappe.get_cached_doc("Customer", customer_name)

	sales_rm = customer.get("custom_relationship_manager") or frappe.db.get_value(
		"Employee", {"user_id": frappe.session.user}, "name"
	)

	rm_name = (customer.get("custom_rm_name") or (
		frappe.db.get_value("Employee", sales_rm, "employee_name") if sales_rm else ""
	))

	doc = frappe.get_doc({
		"doctype": "Insurance Record",
		"customer": customer_name,
		"client_name": customer.customer_name,
		"pan": customer.get("custom_pan"),
		"client_code": customer.get("custom_client_code"),
		"mobile_no": customer.get("custom_mobile"),
		"email": customer.get("custom_email"),
		"insurance_products": insurance_products,
		"rm_employee_code": sales_rm,
		"rm_employee_name": rm_name,
		"branch": customer.get("custom_branch_code") or None,
		"company": frappe.db.get_single_value("Global Defaults", "default_company") or "",
	})

	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True)
	frappe.db.commit()

	return {"name": doc.name, "is_existing": False}


# ---------------------------------------------------------------------------
# EXISTING — get_customer_products (UNCHANGED — 360 panel depends on this)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_customer_products(customer_name):
	"""
	PRD Section 10 — Assigned Products panel
	Returns all products this customer holds across all entities.
	"""
	products = []

	# Insurance Records
	insurance_records = frappe.get_all("Insurance Record",
		filters={"customer": customer_name},
		fields=["name", "insurance_products", "policy_status",
				"policy_number", "policy_expiry_date", "custom_mis_status"])
	for r in insurance_records:
		products.append({
			"type": "Insurance",
			"record": r.name,
			"product": r.insurance_products,
			"status": r.policy_status,
			"reference": r.policy_number,
			"expiry": str(r.policy_expiry_date or ""),
			"mis_status": r.custom_mis_status
		})

	# Bonds Records
	bonds_records = frappe.get_all("Bonds Purchase Record",
		filters={"customer": customer_name},
		fields=["name", "docstatus"])
	for r in bonds_records:
		products.append({
			"type": "Bonds",
			"record": r.name,
			"product": "Bonds",
			"status": "Active" if r.docstatus == 1 else "Draft",
		})

	# Mutual Funds Records
	mf_records = frappe.get_all("Mutual Funds Record",
		filters={"customer": customer_name},
		fields=["name", "docstatus"])
	for r in mf_records:
		products.append({
			"type": "Mutual Funds",
			"record": r.name,
			"product": "Mutual Funds",
			"status": "Active" if r.docstatus == 1 else "Draft",
		})

	# US Subscription Records
	us_records = frappe.get_all("US Subscription Record",
		filters={"customer": customer_name},
		fields=["name", "docstatus"])
	for r in us_records:
		products.append({
			"type": "US Subscription",
			"record": r.name,
			"product": "US Subscription",
			"status": "Active" if r.docstatus == 1 else "Draft",
		})

	return products


# ---------------------------------------------------------------------------
# EXISTING — get_customer_360 (UNCHANGED — signature and return shape kept)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_customer_360(customer=None, customer_name=None):
	cust_name = customer or customer_name
	cust = frappe.get_doc("Customer", cust_name)

	return {
		"customer": {
			"aionion_master_id": cust.get("custom_aionion_master_id"),
			"pan": cust.get("custom_pan"),
			"mobile": cust.get("custom_mobile"),
		},
		"products": {
			"insurance": frappe.get_all("Insurance Record",
				{"customer": cust_name},
				["name", "insurance_products", "policy_number", "policy_status", "policy_expiry_date"]),
			"renewals": frappe.get_all("Insurance Renewal Record",
				{"customer": cust_name},
				["name", "insurance_type", "policy_expiry_date", "renewal_status", "renewals_rm_name"]),
			"us_subscription": frappe.get_all("US Subscription Record",
				{"customer": cust_name},
				["name", "client_status", "amount_paid_us_subs", "subscription_end_date"]),
			"bonds": frappe.get_all("Bonds Purchase Record",
				{"customer": cust_name},
				["name", "number_of_units", "amount_bonds", "execution_date"]),
			"mutual_funds": frappe.get_all("Mutual Funds Record",
				{"customer": cust_name},
				["name", "amount_mf", "order_type"]),
			"equity": frappe.get_all("Equity Record",
				{"customer": cust_name},
				["name", "pan", "client_code"]),
		}
	}


# ---------------------------------------------------------------------------
# EXISTING — sync_customer_product_rms (UNCHANGED)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def sync_customer_product_rms(customer_name):
	"""
	Fetch the most recent RM from each product DocType
	and write them to the Customer's custom RM fields.
	"""
	product_rm_map = {
		"custom_us_rm":        ("US Subscription Record", "sales_done_by"),
		"custom_bonds_rm":     ("Bonds Purchase Record",  "rm_employee_code"),
		"custom_mf_rm":        ("Mutual Funds Record",    "sales_done_by"),
		"custom_equity_rm":    ("Equity Record",          "sales_done_by"),
		"custom_insurance_rm": ("Insurance Record",       "rm_employee_code"),
	}

	updates = {}
	for customer_field, (doctype, rm_field) in product_rm_map.items():
		rows = frappe.get_all(
			doctype,
			filters={"customer": customer_name},
			fields=[rm_field],
			order_by="creation desc",
			limit=1,
		)
		updates[customer_field] = rows[0].get(rm_field) if rows else None

	if any(v for v in updates.values()):
		frappe.db.set_value("Customer", customer_name, updates, update_modified=False)

	return updates


def sync_all_customer_product_rms():
	"""
	Hourly scheduler entry point.
	Iterates every customer and syncs product RMs.
	"""
	customers = frappe.get_all("Customer", fields=["name"], limit=0)
	for c in customers:
		try:
			sync_customer_product_rms(c.name)
		except Exception:
			frappe.log_error(
				title=f"Product RM Sync failed: {c.name}",
				message=frappe.get_traceback(),
			)
	frappe.db.commit()