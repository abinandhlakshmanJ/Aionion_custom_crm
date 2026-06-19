frappe.pages["crm-io"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "CRM Import / Export",
		single_column: true,
	});
	new CRMImportExport(page, wrapper);
};

class CRMImportExport {
	constructor(page, wrapper) {
		this.page = page;
		this.wrapper = wrapper;
		this.make();
	}

	make() {
		this.page.body.css("padding", "20px");
		$(this.html()).appendTo(this.page.body);
		this.bind_events();
	}

	html() {
		return `
<style>
  .cio-card {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 20px 24px;
    margin-bottom: 16px;
  }
  .cio-card h5 {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-color);
    margin: 0 0 4px 0;
  }
  .cio-card p {
    font-size: 12px;
    color: var(--text-muted);
    margin: 0 0 14px 0;
  }
  .cio-section-title {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-muted);
    margin: 24px 0 10px 0;
  }
  .cio-btn-row { display: flex; gap: 10px; flex-wrap: wrap; }
</style>

<div class="cio-section-title">Export</div>
<div class="cio-card">
  <h5>Export US Subscription Records</h5>
  <p>Downloads all Aionion Global leads and their linked US Subscription data as a single CSV file.</p>
  <div class="cio-btn-row">
    <button class="btn btn-default btn-sm" id="cio-export-btn">Export to CSV</button>
    <button class="btn btn-default btn-sm" id="cio-template-btn">Download Import Template</button>
  </div>
</div>

<div class="cio-section-title">Import</div>
<div class="cio-card">
  <h5>Import US Subscription Records</h5>
  <p>Opens Frappe Data Import — upload CSV, map columns to fields, preview and import.</p>
  <div class="cio-btn-row">
    <button class="btn btn-primary btn-sm" id="cio-import-us-btn">Import US Subscription Records</button>
    <button class="btn btn-default btn-sm" id="cio-import-lead-btn">Import CRM Leads</button>
  </div>
</div>

<div class="cio-section-title">Manage</div>
<div class="cio-card">
  <h5>View All Data Imports</h5>
  <p>Check status of past imports, download error logs, and retry failed imports.</p>
  <button class="btn btn-default btn-sm" id="cio-view-imports-btn">View Import History</button>
</div>
		`;
	}

	bind_events() {
		$("#cio-export-btn").on("click", function () {
			$(this).prop("disabled", true).text("Exporting...");
			frappe.call({
				method: "aionion_custom.aionion_custom.api.run_lead_us_export",
				callback(r) {
					$("#cio-export-btn").prop("disabled", false).html("Export to CSV");
					if (r.message && r.message.file_url) {
						window.open(r.message.file_url);
						frappe.show_alert({ message: "Export ready — " + r.message.row_count + " records", indicator: "green" });
					}
				},
				error() {
					$("#cio-export-btn").prop("disabled", false).html("Export to CSV");
				},
			});
		});

		$("#cio-template-btn").on("click", function () {
			$(this).prop("disabled", true).text("Generating...");
			frappe.call({
				method: "aionion_custom.aionion_custom.api.download_import_template",
				callback(r) {
					$("#cio-template-btn").prop("disabled", false).html("Download Import Template");
					if (r.message && r.message.file_url) {
						window.open(r.message.file_url);
						frappe.show_alert({ message: "Template downloaded", indicator: "green" });
					}
				},
				error() {
					$("#cio-template-btn").prop("disabled", false).html("Download Import Template");
				},
			});
		});

		$("#cio-import-us-btn").on("click", function () {
			frappe.new_doc("Data Import", {
				reference_doctype: "US Subscription Record",
				import_type: "Insert New Records"
			});
		});

		$("#cio-import-lead-btn").on("click", function () {
			frappe.new_doc("Data Import", {
				reference_doctype: "CRM Lead",
				import_type: "Insert New Records"
			});
		});

		$("#cio-view-imports-btn").on("click", function () {
			frappe.set_route("List", "Data Import");
		});
	}
}
