frappe.pages["call-log-dashboard"].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Call Log Dashboard",
        single_column: true
    });
    $(frappe.render_template("call_log_dashboard", {})).appendTo(page.body);
    var css = [
        ".cld-wrap { padding: 0; }",
        ".cld-kpi-row { display: grid; grid-template-columns: repeat(5,1fr); gap: 10px; margin-bottom: 18px; }",
        "@media(max-width:800px){ .cld-kpi-row { grid-template-columns: repeat(3,1fr); } }",
        ".cld-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--border-radius); padding: 12px 16px; border-top: 3px solid var(--primary); }",
        ".cld-card.cld-in { border-top-color: #00BFA5; }",
        ".cld-card.cld-out { border-top-color: #1976D2; }",
        ".cld-card.cld-miss { border-top-color: #E53935; }",
        ".cld-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }",
        ".cld-val { font-size: 24px; font-weight: 700; color: var(--heading-color); }",
        ".cld-section-title { font-size: 13px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }",
        ".cld-table { width: 100%; border-collapse: collapse; font-size: 13px; }",
        ".cld-table th { padding: 8px 10px; text-align: left; font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.4px; border-bottom: 2px solid var(--border-color); background: var(--subtle-fg); }",
        ".cld-table td { padding: 9px 10px; border-bottom: 1px solid var(--border-color); color: var(--text-color); }",
        ".cld-table tbody tr:hover { background: var(--hover-bg); }",
        ".b-in { color: #00796B; font-weight: 600; }",
        ".b-out { color: #1565C0; font-weight: 600; }",
        ".b-miss { color: #C62828; font-weight: 600; }",
        ".cld-empty { text-align: center; padding: 24px; color: var(--text-muted); font-size: 13px; }",
        ".cld-view-btn { color: var(--primary); font-size: 12px; cursor: pointer; border: none; background: none; padding: 0; }",
        ".cld-view-btn:hover { text-decoration: underline; }",
        ".cld-load-more { display: block; margin: 14px auto 4px; padding: 5px 24px; border: 1px solid var(--border-color); border-radius: 20px; background: transparent; cursor: pointer; font-size: 12px; color: var(--text-muted); }",
        ".cld-load-more:hover { border-color: var(--primary); color: var(--primary); }",
        ".cld-detail-panel { margin-top: 20px; border: 1px solid var(--border-color); border-radius: var(--border-radius); overflow: hidden; }",
        ".cld-detail-header { display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; background: var(--subtle-fg); border-bottom: 1px solid var(--border-color); }",
        ".cld-log-item { display: grid; grid-template-columns: 60px 1fr 80px 140px; gap: 12px; align-items: center; padding: 9px 16px; border-bottom: 1px solid var(--border-color); font-size: 12px; }",
        ".cld-log-lead { color: var(--text-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }",
        ".cld-log-time { color: var(--text-muted); font-size: 11px; text-align: right; }",
        ".dim-row { opacity: 0.4; }"
    ].join("");
    $("<style>").text(css).appendTo("head");
    var today = frappe.datetime.get_today();
    var first_of_month = today.substring(0,8) + "01";
    // Standard Frappe toolbar date fields
    window._fd = page.add_field({
        fieldtype: "Date", fieldname: "from_date", label: "From Date",
        default: first_of_month,
        change: function() { window._ds.offset = 0; reload_all(); }
    });
    window._td = page.add_field({
        fieldtype: "Date", fieldname: "to_date", label: "To Date",
        default: today,
        change: function() { window._ds.offset = 0; reload_all(); }
    });
    // Search in toolbar
    window._sd = page.add_field({
        fieldtype: "Data", fieldname: "search", label: "Search Employee",
        change: frappe.utils.debounce(function() {
            window._ds.search = window._sd.get_value() || "";
            window._ds.offset = 0;
            load_leaderboard(false); hide_detail();
        }, 400)
    });
    // Quick preset buttons
    page.add_inner_button("Today", function() {
        window._fd.set_value(today); window._td.set_value(today);
    });
    page.add_inner_button("This Week", function() {
        window._fd.set_value(frappe.datetime.add_days(today, -7));
        window._td.set_value(today);
    });
    page.add_inner_button("This Month", function() {
        window._fd.set_value(first_of_month); window._td.set_value(today);
    });
    window._ds = { offset: 0, search: "", loading: false };
    reload_all();
    $(page.body).on("click", ".cld-load-more", function() {
        window._ds.offset += 20; load_leaderboard(true);
    });
    $(page.body).on("click", "#close-detail", hide_detail);
    $(page.body).on("click", ".cld-view-btn", function() {
        load_emp_detail($(this).data("email"), $(this).data("name"));
    });
};
function get_dates() {
    return {
        from_date: (window._fd && window._fd.get_value()) || null,
        to_date: (window._td && window._td.get_value()) || null
    };
}
function reload_all() { load_summary(); load_leaderboard(false); hide_detail(); }
function hide_detail() { $("#emp-detail-panel").hide(); }
function load_summary() {
    var d = get_dates();
    frappe.call({
        method: "aionion_custom.aionion_custom.controllers.call_log_api.get_call_log_summary",
        args: { from_date: d.from_date, to_date: d.to_date },
        callback: function(r) {
            if (!r.message) return; var m = r.message;
            $("#val-total").text(m.total || 0);
            $("#val-incoming").text(m.incoming || 0);
            $("#val-outgoing").text(m.outgoing || 0);
            $("#val-missed").text(m.missed || 0);
            var dur = m.avg_duration || 0;
            $("#val-avg").text(dur >= 60 ? Math.floor(dur/60)+"m "+(dur%60)+"s" : dur+"s");
        }
    });
}
function load_leaderboard(append) {
    var s = window._ds; if (s.loading) return; s.loading = true;
    var d = get_dates();
    var tbody = $("#leaderboard-body");
    if (!append) { tbody.html('<tr><td colspan="9" class="cld-empty">Loading...</td></tr>'); $(".cld-load-more").remove(); }
    frappe.call({
        method: "aionion_custom.aionion_custom.controllers.call_log_api.get_calls_per_employee",
        args: { from_date: d.from_date, to_date: d.to_date, search: s.search, limit: 20, offset: s.offset },
        callback: function(r) {
            s.loading = false;
            if (!append) tbody.empty();
            $(".cld-load-more").remove();
            if (!r.message || !r.message.length) {
                if (!append) tbody.append('<tr><td colspan="9" class="cld-empty">No employees found</td></tr>');
                return;
            }
            var start = s.offset;
            r.message.forEach(function(e, i) {
                var cls = e.total === 0 ? " class='dim-row'" : "";
                tbody.append("<tr"+cls+">" +
                    "<td style='color:var(--text-muted);font-size:12px;'>"+(start+i+1)+"</td>" +
                    "<td>"+e.employee_name+"</td>" +
                    "<td style='color:var(--text-muted);'>"+(e.designation||"-")+"</td>" +
                    "<td style='color:var(--text-muted);'>"+(e.reports_to_name||"-")+"</td>" +
                    "<td style='text-align:center;'><span class='b-in'>"+e.incoming+"</span></td>" +
                    "<td style='text-align:center;'><span class='b-out'>"+e.outgoing+"</span></td>" +
                    "<td style='text-align:center;'><span class='b-miss'>"+e.missed+"</span></td>" +
                    "<td style='text-align:center;font-weight:600;'>"+e.total+"</td>" +
                    "<td><button class='cld-view-btn' data-email='"+e.user_email+"' data-name='"+e.employee_name+"'>View</button></td>" +
                    "</tr>");
            });
            if (r.message.length === 20) {
                $("<button class='cld-load-more'>Load More</button>").insertAfter(".cld-table");
            }
        }
    });
}
function load_emp_detail(email, name) {
    var d = get_dates();
    $("#detail-emp-name").text(name);
    $("#detail-body").html('<div class="cld-empty">Loading...</div>');
    $("#emp-detail-panel").show();
    $("html,body").animate({ scrollTop: $("#emp-detail-panel").offset().top - 80 }, 250);
    frappe.call({
        method: "aionion_custom.aionion_custom.controllers.call_log_api.get_employee_call_detail",
        args: { user_email: email, from_date: d.from_date, to_date: d.to_date },
        callback: function(r) {
            var body = $("#detail-body"); body.empty();
            if (!r.message || !r.message.length) {
                body.html('<div class="cld-empty">No calls in this date range</div>'); return;
            }
            r.message.forEach(function(c) {
                var type_cls = c.type === "Incoming" ? "b-in" : "b-out";
                var lead = c.lead_full_name || "Unknown";
                var dur = c.duration ? (c.duration >= 60 ? Math.floor(c.duration/60)+"m "+(c.duration%60)+"s" : c.duration+"s") : "-";
                body.append("<div class='cld-log-item'>" +
                    "<span class='"+type_cls+"'>"+c.type+"</span>" +
                    "<span class='cld-log-lead'>"+lead+"</span>" +
                    "<span style='color:var(--text-muted);'>"+dur+"</span>" +
                    "<span class='cld-log-time'>"+frappe.datetime.str_to_user(c.creation)+"</span>" +
                    "</div>");
            });
        }
    });
}