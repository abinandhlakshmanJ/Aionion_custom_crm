frappe.pages["crm-io"].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({parent:wrapper,title:"CRM Import Export",single_column:true});

    page.body.html(`
        <div style="padding:40px">
            <div class="row">
                <div class="col-md-5">
                    <div class="card" style="border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.1);padding:40px;text-align:center">
                        <div style="font-size:48px;margin-bottom:12px">⬇</div>
                        <h4 style="font-weight:600">Export to CSV</h4>
                        <p class="text-muted" style="font-size:13px;margin-bottom:20px">Downloads all CRM Leads with US Subscription Records</p>
                        <button id="btn-export" class="btn btn-success btn-lg" style="width:100%">Export CSV</button>
                        <div id="export-status" class="mt-3" style="font-size:13px"></div>
                    </div>
                </div>
                <div class="col-md-2 d-flex align-items-center justify-content-center">
                    <span class="text-muted" style="font-size:36px">⇄</span>
                </div>
                <div class="col-md-5">
                    <div class="card" style="border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.1);padding:40px;text-align:center">
                        <div style="font-size:48px;margin-bottom:12px">⬆</div>
                        <h4 style="font-weight:600">Import from CSV</h4>
                        <p class="text-muted" style="font-size:13px;margin-bottom:20px">Upload exported CSV to restore lead and subscription data</p>
                        <button id="btn-import" class="btn btn-primary btn-lg" style="width:100%">Import CSV</button>
                        <div id="import-status" class="mt-3" style="font-size:13px"></div>
                    </div>
                </div>
            </div>
        </div>
    `);

    page.body.find("#btn-export").on("click", function() {
        var btn=page.body.find("#btn-export"),status=page.body.find("#export-status");
        btn.prop("disabled",true).text("Exporting...");status.html("");
        fetch("/api/method/aionion_custom.api.lead_us_import_export.export_csv",{
            method:"GET",headers:{"X-Frappe-CSRF-Token":frappe.csrf_token}
        }).then(r=>r.blob()).then(blob=>{
            var a=document.createElement("a");
            a.href=URL.createObjectURL(blob);a.download="lead_us_export.csv";a.click();
            status.html('<span style="color:green">✅ Export complete</span>');
        }).catch(e=>status.html('<span style="color:red">❌ '+e.message+'</span>'))
        .finally(()=>btn.prop("disabled",false).text("Export CSV"));
    });

    page.body.find("#btn-import").on("click", function() {
        var status=page.body.find("#import-status");
        new frappe.ui.FileUploader({
            restrictions:{allowed_file_types:[".csv"]},
            on_success:function(file){
                status.html('<span class="text-muted">⏳ Importing... please wait</span>');
                frappe.call({
                    method:"aionion_custom.api.lead_us_import_export.import_csv",
                    args:{file_url:file.file_url},freeze:true,freeze_message:"Importing records...",
                    callback:function(r){
                        var res=r.message,fails=res.failed||[];
                        status.html(fails.length===0
                            ?'<span style="color:green">✅ '+res.success+' records imported</span>'
                            :'<span style="color:orange">⚠ '+res.success+' ok, '+fails.length+' failed — check Error Log</span>');
                    }
                });
            }
        });
    });
};