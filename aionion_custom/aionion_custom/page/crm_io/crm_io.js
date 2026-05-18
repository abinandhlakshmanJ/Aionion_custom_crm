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
		this.uploaded_file_url = null;
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
  .cio-drop-zone {
    border: 2px dashed var(--border-color);
    border-radius: 8px;
    padding: 32px;
    text-align: center;
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s;
    background: var(--fg-color);
  }
  .cio-drop-zone:hover, .cio-drop-zone.dragover {
    border-color: var(--primary);
    background: var(--primary-light);
  }
  .cio-drop-zone .icon { font-size: 28px; margin-bottom: 8px; color: var(--text-muted); }
  .cio-drop-zone .label { font-size: 13px; font-weight: 500; color: var(--text-color); }
  .cio-drop-zone .sublabel { font-size: 11px; color: var(--text-muted); margin-top: 4px; }
  .cio-file-chosen {
    display: none;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    background: var(--fg-color);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    font-size: 12px;
    color: var(--text-color);
  }
  .cio-file-chosen .fname { font-weight: 600; flex: 1; }
  .cio-preview-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 11px;
    overflow-x: auto;
    display: block;
    white-space: nowrap;
  }
  .cio-preview-table th {
    background: var(--subtle-fg);
    padding: 6px 10px;
    text-align: left;
    font-weight: 600;
    border: 1px solid var(--border-color);
    color: var(--text-muted);
  }
  .cio-preview-table td {
    padding: 5px 10px;
    border: 1px solid var(--border-color);
    max-width: 160px;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .cio-results {
    display: none;
  }
  .cio-stat-box {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    padding: 14px 24px;
    border-radius: 8px;
    margin-right: 12px;
    min-width: 100px;
  }
  .cio-stat-box .num { font-size: 28px; font-weight: 700; }
  .cio-stat-box .lbl { font-size: 11px; margin-top: 2px; font-weight: 500; }
  .cio-stat-box.success { background: #d4edda; color: #155724; }
  .cio-stat-box.failed  { background: #f8d7da; color: #721c24; }
  .cio-error-list {
    margin-top: 12px;
    max-height: 240px;
    overflow-y: auto;
    font-size: 11px;
    font-family: monospace;
    background: var(--fg-color);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    padding: 10px;
    white-space: pre-wrap;
    word-break: break-all;
  }
  .cio-spinner { display: none; text-align: center; padding: 20px; color: var(--text-muted); font-size: 13px; }
</style>

<!-- ── EXPORT ── -->
<div class="cio-section-title">📤 Export</div>
<div class="cio-card">
  <h5>Export CRM Leads + US Subscription Records</h5>
  <p>Downloads all existing leads and their linked US Subscription data as a single CSV file.</p>
  <button class="btn btn-default btn-sm" id="cio-export-btn">
    <span>⬇ Export to CSV</span>
  </button>
</div>

<!-- ── TEMPLATE ── -->
<div class="cio-section-title">📋 Template</div>
<div class="cio-card">
  <h5>Download Import Template</h5>
  <p>Blank CSV with all column headers pre-filled — use this as the starting point for your data.</p>
  <button class="btn btn-default btn-sm" id="cio-template-btn">
    <span>⬇ Download Template</span>
  </button>
</div>

<!-- ── IMPORT ── -->
<div class="cio-section-title">📥 Import</div>
<div class="cio-card">
  <h5>Import CRM Leads + US Subscription Records</h5>
  <p>Upload a CSV with <code>lead__</code> and <code>us__</code> prefixed columns. Both Lead and US Subscription are created/updated in one shot.</p>

  <!-- Drop Zone -->
  <div class="cio-drop-zone" id="cio-drop-zone">
    <div class="icon">📁</div>
    <div class="label">Click to upload or drag & drop</div>
    <div class="sublabel">CSV files only · lead__ and us__ columns</div>
    <input type="file" id="cio-file-input" accept=".csv" style="display:none">
  </div>

  <!-- File chosen indicator -->
  <div class="cio-file-chosen" id="cio-file-chosen">
    <span>📄</span>
    <span class="fname" id="cio-fname"></span>
    <a href="#" id="cio-change-file" style="font-size:11px;color:var(--primary)">Change</a>
  </div>

  <!-- Preview -->
  <div id="cio-preview-wrap" style="display:none;margin-top:16px;">
    <div style="font-size:12px;font-weight:600;margin-bottom:8px;color:var(--text-muted);">
      Preview — first 5 rows
    </div>
    <div id="cio-preview-container" style="overflow-x:auto;"></div>
    <div style="margin-top:14px;">
      <button class="btn btn-primary btn-sm" id="cio-import-btn">🚀 Start Import</button>
      <span style="font-size:11px;color:var(--text-muted);margin-left:10px;" id="cio-row-hint"></span>
    </div>
  </div>

  <!-- Spinner -->
  <div class="cio-spinner" id="cio-spinner">
    <div class="text-muted" style="margin-bottom:8px;">⏳ Importing records... this may take a few minutes</div>
    <div class="progress" style="height:6px;width:100%;background:var(--border-color);border-radius:3px;">
      <div class="progress-bar progress-bar-striped active" style="width:100%;background:var(--primary);height:100%;border-radius:3px;"></div>
    </div>
  </div>

  <!-- Results -->
  <div class="cio-results" id="cio-results" style="margin-top:16px;">
    <div>
      <span class="cio-stat-box success">
        <span class="num" id="cio-success-count">0</span>
        <span class="lbl">✅ Imported</span>
      </span>
      <span class="cio-stat-box failed">
        <span class="num" id="cio-failed-count">0</span>
        <span class="lbl">❌ Failed</span>
      </span>
    </div>
    <div id="cio-error-wrap" style="display:none;margin-top:12px;">
      <div style="font-size:12px;font-weight:600;margin-bottom:6px;color:#721c24;">Failed Rows</div>
      <div class="cio-error-list" id="cio-error-list"></div>
    </div>
    <div style="margin-top:14px;">
      <button class="btn btn-default btn-sm" id="cio-reset-btn">↩ Import Another File</button>
    </div>
  </div>
</div>
		`;
	}

	bind_events() {
		const self = this;

		// ── Export ──────────────────────────────────────────────
		$("#cio-export-btn").on("click", function () {
			$(this).prop("disabled", true).text("Exporting...");
			frappe.call({
				method: "aionion_custom.aionion_custom.api.run_lead_us_export",
				callback(r) {
					$("#cio-export-btn").prop("disabled", false).html("⬇ Export to CSV");
					if (r.message && r.message.file_url) {
						window.open(r.message.file_url);
						frappe.show_alert({ message: "Export ready — downloading", indicator: "green" });
					}
				},
				error() {
					$("#cio-export-btn").prop("disabled", false).html("⬇ Export to CSV");
				},
			});
		});

		// ── Template ────────────────────────────────────────────
		$("#cio-template-btn").on("click", function () {
			$(this).prop("disabled", true).text("Generating...");
			frappe.call({
				method: "aionion_custom.aionion_custom.api.download_import_template",
				callback(r) {
					$("#cio-template-btn").prop("disabled", false).html("⬇ Download Template");
					if (r.message && r.message.file_url) {
						window.open(r.message.file_url);
					}
				},
				error() {
					$("#cio-template-btn").prop("disabled", false).html("⬇ Download Template");
				},
			});
		});

		// ── File Upload — click ─────────────────────────────────
		$("#cio-drop-zone").on("click", function () {
			$("#cio-file-input").click();
		});

		$("#cio-change-file").on("click", function (e) {
			e.preventDefault();
			self.reset_import_state();
			$("#cio-file-input").click();
		});

		// ── Drag & Drop ─────────────────────────────────────────
		const zone = document.getElementById("cio-drop-zone");
		zone.addEventListener("dragover", (e) => {
			e.preventDefault();
			$("#cio-drop-zone").addClass("dragover");
		});
		zone.addEventListener("dragleave", () => {
			$("#cio-drop-zone").removeClass("dragover");
		});
		zone.addEventListener("drop", (e) => {
			e.preventDefault();
			$("#cio-drop-zone").removeClass("dragover");
			const file = e.dataTransfer.files[0];
			if (file) self.handle_file(file);
		});

		// ── File Input Change ───────────────────────────────────
		$("#cio-file-input").on("change", function () {
			const file = this.files[0];
			if (file) self.handle_file(file);
		});

		// ── Import ──────────────────────────────────────────────
		$("#cio-import-btn").on("click", function () {
			if (!self.uploaded_file_url) {
				frappe.show_alert({ message: "Please upload a CSV file first", indicator: "orange" });
				return;
			}
			self.run_import();
		});

		// ── Reset ───────────────────────────────────────────────
		$("#cio-reset-btn").on("click", function () {
			self.reset_import_state();
		});
	}

	handle_file(file) {
		if (!file.name.endsWith(".csv")) {
			frappe.show_alert({ message: "Please upload a CSV file", indicator: "red" });
			return;
		}

		// Show file name indicator
		$("#cio-drop-zone").hide();
		$("#cio-file-chosen").css("display", "flex");
		$("#cio-fname").text(file.name);
		$("#cio-preview-wrap").hide();
		$("#cio-results").hide();

		// Upload file to Frappe
		frappe.show_alert({ message: "Uploading file...", indicator: "blue" });

		const formData = new FormData();
		formData.append("file", file, file.name);
		formData.append("is_private", 1);
		formData.append("folder", "Home");

		fetch("/api/method/upload_file", {
			method: "POST",
			headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
			body: formData,
		})
			.then((res) => res.json())
			.then((data) => {
				if (data.message && data.message.file_url) {
					this.uploaded_file_url = data.message.file_url;
					frappe.show_alert({ message: "File uploaded — loading preview", indicator: "green" });
					this.load_preview(data.message.file_url, file.name);
				} else {
					frappe.show_alert({ message: "Upload failed", indicator: "red" });
				}
			})
			.catch(() => {
				frappe.show_alert({ message: "Upload failed", indicator: "red" });
			});
	}

	load_preview(file_url, file_name) {
		const self = this;
		frappe.call({
			method: "aionion_custom.aionion_custom.api.preview_import_file",
			args: { file_url },
			callback(r) {
				if (!r.message) return;
				const { headers, rows } = r.message;

				// Count total rows by reading a hint from file name — just show preview
				let table = `<table class="cio-preview-table"><thead><tr>`;
				// Only show key columns in preview to keep it readable
				const key_cols = headers.filter(
					(h) =>
						["lead__name", "lead__first_name", "lead__last_name", "lead__email",
						 "lead__mobile_no", "lead__custom_entity", "us__name", "us__lead",
						 "us__client_name", "us__payment_status", "us__us_status"].includes(h)
				);
				const preview_cols = key_cols.length > 0 ? key_cols : headers.slice(0, 10);

				preview_cols.forEach((h) => {
					table += `<th>${h.replace("lead__", "").replace("us__", "🔵 ")}</th>`;
				});
				table += `</tr></thead><tbody>`;

				rows.forEach((row) => {
					table += "<tr>";
					preview_cols.forEach((h) => {
						table += `<td title="${row[h] || ""}">${row[h] || "<span style='color:var(--text-muted)'>—</span>"}</td>`;
					});
					table += "</tr>";
				});
				table += `</tbody></table>`;

				$("#cio-preview-container").html(table);
				$("#cio-row-hint").text(`Showing ${rows.length} of total rows — all columns will be imported`);
				$("#cio-preview-wrap").show();
			},
		});
	}

	run_import() {
		const self = this;
		$("#cio-import-btn").prop("disabled", true);
		$("#cio-preview-wrap").hide();
		$("#cio-spinner").show();
		$("#cio-results").hide();

		frappe.call({
			method: "aionion_custom.aionion_custom.api.run_lead_us_import",
			args: { file_url: this.uploaded_file_url },
			timeout: 600, // 10 minutes for large imports
			callback(r) {
				$("#cio-spinner").hide();
				if (!r.message) return;

				const { success, failed } = r.message;
				$("#cio-success-count").text(success || 0);
				$("#cio-failed-count").text((failed || []).length);
				$("#cio-results").show();

				if (failed && failed.length > 0) {
					$("#cio-error-wrap").show();
					$("#cio-error-list").text(failed.join("\n\n"));
				} else {
					$("#cio-error-wrap").hide();
				}

				frappe.show_alert({
					message: `Import complete — ${success} success, ${(failed || []).length} failed`,
					indicator: (failed || []).length === 0 ? "green" : "orange",
				});
			},
			error() {
				$("#cio-spinner").hide();
				$("#cio-import-btn").prop("disabled", false);
				$("#cio-preview-wrap").show();
				frappe.show_alert({ message: "Import failed — check Error Log", indicator: "red" });
			},
		});
	}

	reset_import_state() {
		this.uploaded_file_url = null;
		$("#cio-file-input").val("");
		$("#cio-drop-zone").show();
		$("#cio-file-chosen").hide();
		$("#cio-preview-wrap").hide();
		$("#cio-spinner").hide();
		$("#cio-results").hide();
		$("#cio-import-btn").prop("disabled", false);
	}
}
