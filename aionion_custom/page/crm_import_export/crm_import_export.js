frappe.pages["crm-import-export"].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "CRM Import Export",
        single_column: true,
    });

    // Render HTML directly into page body
    $(frappe.render_template("crm_import_export", {})).appendTo(page.body);

    // Bind Export button
    page.body.find("#btn-export").on("click", function () {
        var btn    = page.body.find("#btn-export");
        var status = page.body.find("#export-status");

        btn.prop("disabled", true).text("Exporting…");
        status.html("");

        fetch("/api/method/aionion_custom.api.lead_us_import_export.export_csv", {
            method: "GET",
            headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
        })
        .then(function (response) {
            if (!response.ok) throw new Error("Export failed: " + response.statusText);
            return response.blob();
        })
        .then(function (blob) {
            var url    = URL.createObjectURL(blob);
            var anchor = document.createElement("a");
            anchor.href     = url;
            anchor.download = "lead_us_export.csv";
            anchor.click();
            URL.revokeObjectURL(url);
            status.html('<span style="color:green;">✅ Export complete — file downloading.</span>');
        })
        .catch(function (err) {
            status.html('<span style="color:red;">❌ ' + err.message + "</span>");
        })
        .finally(function () {
            btn.prop("disabled", false).text("Export CSV");
        });
    });

    // Bind Import button
    page.body.find("#btn-import").on("click", function () {
        var status = page.body.find("#import-status");
        status.html('<span class="text-muted">Opening file picker…</span>');

        new frappe.ui.FileUploader({
            restrictions: { allowed_file_types: [".csv"] },
            on_success: function (file) {
                status.html('<span class="text-muted">⏳ Importing… please wait.</span>');

                frappe.call({
                    method: "aionion_custom.api.lead_us_import_export.import_csv",
                    args: { file_url: file.file_url },
                    freeze: true,
                    freeze_message: "Importing records…",
                    callback: function (r) {
                        if (r.exc) {
                            status.html('<span style="color:red;">❌ Import error — check Error Log.</span>');
                            return;
                        }
                        var res   = r.message;
                        var fails = res.failed || [];

                        if (fails.length === 0) {
                            status.html(
                                '<span style="color:green;">✅ Import complete — ' + res.success + " records imported.</span>"
                            );
                        } else {
                            var html = '<span style="color:orange;">⚠ ' + res.success + " succeeded, " + fails.length + " failed.</span><ul style='text-align:left;color:red;font-size:12px;margin-top:8px;'>";
                            fails.forEach(function (f) { html += "<li>" + f + "</li>"; });
                            html += "</ul>";
                            status.html(html);
                        }
                    },
                });
            },
        });
    });
};
