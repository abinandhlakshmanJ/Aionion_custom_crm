frappe.pages["aionion-team-activity"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Team Activity Dashboard",
        single_column: true
    });

    const from_date = page.add_field({
        fieldname: "from_date",
        label: "From Date",
        fieldtype: "Date",
        default: frappe.datetime.get_today(),
        change() { load_all(); }
    });

    const to_date = page.add_field({
        fieldname: "to_date",
        label: "To Date",
        fieldtype: "Date",
        default: frappe.datetime.get_today(),
        change() { load_all(); }
    });

    page.add_action_item("Refresh", () => load_all());

    $(`
        <style>
            .ata-wrap { padding: 20px; font-family: inherit; }

            /* Summary Cards */
            .ata-summary-grid {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 14px;
                margin-bottom: 24px;
            }
            @media (max-width: 768px) {
                .ata-summary-grid { grid-template-columns: repeat(2, 1fr); }
            }
            .ata-card {
                border-radius: 16px;
                padding: 20px 16px;
                text-align: center;
                position: relative;
                overflow: hidden;
            }
            .ata-card .ata-card-icon {
                font-size: 28px;
                margin-bottom: 8px;
            }
            .ata-card .ata-card-label {
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.8px;
                text-transform: uppercase;
                opacity: 0.75;
                margin-bottom: 6px;
            }
            .ata-card .ata-card-value {
                font-size: 36px;
                font-weight: 800;
                line-height: 1;
            }
            .ata-card .ata-card-sub {
                font-size: 11px;
                opacity: 0.65;
                margin-top: 6px;
            }
            .ata-card.indigo  { background: linear-gradient(135deg,#e0e7ff,#c7d2fe); color:#3730a3; }
            .ata-card.green   { background: linear-gradient(135deg,#dcfce7,#bbf7d0); color:#166534; }
            .ata-card.red     { background: linear-gradient(135deg,#fee2e2,#fecaca); color:#991b1b; }
            .ata-card.amber   { background: linear-gradient(135deg,#fef9c3,#fde68a); color:#92400e; }
            .ata-card.cyan    { background: linear-gradient(135deg,#cffafe,#a5f3fc); color:#155e75; }
            .ata-card.purple  { background: linear-gradient(135deg,#f3e8ff,#e9d5ff); color:#6b21a8; }
            .ata-card.pink    { background: linear-gradient(135deg,#fce7f3,#fbcfe8); color:#9d174d; }
            .ata-card.slate   { background: linear-gradient(135deg,#f1f5f9,#e2e8f0); color:#334155; }

            /* Section Header */
            .ata-section-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 14px;
            }
            .ata-section-title {
                font-size: 15px;
                font-weight: 700;
                color: #1e293b;
            }
            .ata-section-sub {
                font-size: 12px;
                color: #94a3b8;
                margin-top: 2px;
            }

            /* Tabs */
            .ata-tabs {
                display: flex;
                gap: 6px;
                padding: 4px;
                background: #f1f5f9;
                border-radius: 10px;
                margin-bottom: 20px;
                width: fit-content;
            }
            .ata-tab {
                border: none;
                background: transparent;
                padding: 8px 20px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
                color: #64748b;
                cursor: pointer;
                transition: all 0.2s;
            }
            .ata-tab.active {
                background: #fff;
                color: #4361ee;
                box-shadow: 0 1px 4px rgba(0,0,0,0.12);
            }

            /* Panel Card */
            .ata-panel {
                background: #fff;
                border-radius: 16px;
                border: 1px solid #e2e8f0;
                padding: 24px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.04);
                margin-bottom: 20px;
            }

            /* Table */
            .ata-table { width: 100%; border-collapse: separate; border-spacing: 0; }
            .ata-table thead th {
                background: #f8fafc;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.6px;
                text-transform: uppercase;
                color: #64748b;
                padding: 10px 14px;
                border-bottom: 2px solid #e2e8f0;
                white-space: nowrap;
                position: sticky;
                top: 0;
            }
            .ata-table thead th:first-child { border-radius: 8px 0 0 0; }
            .ata-table thead th:last-child  { border-radius: 0 8px 0 0; }
            .ata-table tbody tr { transition: background 0.15s; }
            .ata-table tbody tr:hover { background: #f8fafc; }
            .ata-table tbody td {
                padding: 10px 14px;
                font-size: 13px;
                border-bottom: 1px solid #f1f5f9;
                color: #334155;
                vertical-align: middle;
            }
            .ata-table tbody tr.manager-row td {
                background: #f8fafc;
                font-weight: 700;
                border-left: 3px solid #6366f1;
            }
            .ata-table tbody tr.manager-row td:not(:first-child) {
                border-left: none;
            }

            /* Badges */
            .ata-badge {
                display: inline-flex;
                align-items: center;
                padding: 3px 10px;
                border-radius: 99px;
                font-size: 11px;
                font-weight: 700;
            }
            .badge-green  { background: #dcfce7; color: #166534; }
            .badge-red    { background: #fee2e2; color: #991b1b; }
            .badge-blue   { background: #dbeafe; color: #1e40af; }
            .badge-amber  { background: #fef9c3; color: #92400e; }
            .badge-purple { background: #f3e8ff; color: #6b21a8; }

            /* Number highlights */
            .num-high   { color: #166534; font-weight: 700; }
            .num-medium { color: #92400e; font-weight: 600; }
            .num-zero   { color: #94a3b8; }

            /* Loading */
            .ata-loading {
                text-align: center;
                padding: 40px;
                color: #94a3b8;
                font-size: 14px;
            }
            .ata-loading .spinner {
                width: 32px; height: 32px;
                border: 3px solid #e2e8f0;
                border-top-color: #6366f1;
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
                margin: 0 auto 12px;
            }
            @keyframes spin { to { transform: rotate(360deg); } }

            /* Scrollable table */
            .ata-table-wrap {
                overflow-x: auto;
                border-radius: 10px;
                border: 1px solid #e2e8f0;
            }
        </style>

        <div class="ata-wrap">

            <!-- Row 1: Team Overview Cards -->
            <div class="ata-summary-grid" id="summary-cards">
                <div class="ata-card indigo">
                    <div class="ata-card-icon">👥</div>
                    <div class="ata-card-label">Team Strength</div>
                    <div class="ata-card-value" id="card-strength">—</div>
                    <div class="ata-card-sub">Active employees</div>
                </div>
                <div class="ata-card green">
                    <div class="ata-card-icon">✅</div>
                    <div class="ata-card-label">Logged In</div>
                    <div class="ata-card-value" id="card-loggedin">—</div>
                    <div class="ata-card-sub" id="card-loggedin-pct">of team today</div>
                </div>
                <div class="ata-card red">
                    <div class="ata-card-icon">❌</div>
                    <div class="ata-card-label">Not Logged In</div>
                    <div class="ata-card-value" id="card-notloggedin">—</div>
                    <div class="ata-card-sub" id="card-notloggedin-pct">of team today</div>
                </div>
                <div class="ata-card amber">
                    <div class="ata-card-icon">📋</div>
                    <div class="ata-card-label">Leads Today</div>
                    <div class="ata-card-value" id="card-leads-today">—</div>
                    <div class="ata-card-sub">Team total</div>
                </div>
                <div class="ata-card cyan">
                    <div class="ata-card-icon">🗂️</div>
                    <div class="ata-card-label">Total Leads</div>
                    <div class="ata-card-value" id="card-total-leads">—</div>
                    <div class="ata-card-sub">All time</div>
                </div>
                <div class="ata-card purple">
                    <div class="ata-card-icon">✉️</div>
                    <div class="ata-card-label">Emails Today</div>
                    <div class="ata-card-value" id="card-emails-today">—</div>
                    <div class="ata-card-sub">Team total</div>
                </div>
                <div class="ata-card pink">
                    <div class="ata-card-icon">📞</div>
                    <div class="ata-card-label">Calls Today</div>
                    <div class="ata-card-value" id="card-calls-today">—</div>
                    <div class="ata-card-sub">Team total</div>
                </div>
                <div class="ata-card slate">
                    <div class="ata-card-icon">📊</div>
                    <div class="ata-card-label">Activity Score</div>
                    <div class="ata-card-value" id="card-activity-score">—</div>
                    <div class="ata-card-sub">Leads+Emails+Calls</div>
                </div>
            </div>

            <!-- Tabs -->
            <div class="ata-tabs">
                <button class="ata-tab active" data-tab="team">👥 Team Hierarchy</button>
                <button class="ata-tab" data-tab="individual">👤 Individual View</button>
            </div>

            <!-- Panel: Team Hierarchy -->
            <div class="ata-panel" id="panel-team">
                <div class="ata-section-header">
                    <div>
                        <div class="ata-section-title">Team Hierarchy Activity</div>
                        <div class="ata-section-sub">Rolled up stats per manager and their team</div>
                    </div>
                </div>
                <div class="ata-table-wrap">
                    <div id="team-table-body">
                        <div class="ata-loading"><div class="spinner"></div>Loading team data...</div>
                    </div>
                </div>
            </div>

            <!-- Panel: Individual -->
            <div class="ata-panel" id="panel-individual" style="display:none;">
                <div class="ata-section-header">
                    <div>
                        <div class="ata-section-title">Individual Activity</div>
                        <div class="ata-section-sub">Each employee's own activity for the period</div>
                    </div>
                    <input type="text" id="ata-search" placeholder="🔍 Search employee..." 
                        style="padding:7px 12px;border:1px solid #e2e8f0;border-radius:8px;font-size:13px;width:220px;">
                </div>
                <div class="ata-table-wrap">
                    <div id="individual-table-body">
                        <div class="ata-loading"><div class="spinner"></div>Loading...</div>
                    </div>
                </div>
            </div>

        </div>
    `).appendTo(page.main);

    // Tab switching
    $(".ata-tab").on("click", function() {
        $(".ata-tab").removeClass("active");
        $(this).addClass("active");
        const tab = $(this).data("tab");
        if (tab === "team") {
            $("#panel-team").show();
            $("#panel-individual").hide();
        } else {
            $("#panel-team").hide();
            $("#panel-individual").show();
        }
    });

    // Search filter for individual table
    $("#ata-search").on("input", function() {
        const q = $(this).val().toLowerCase();
        $("#individual-table-body tbody tr").each(function() {
            $(this).toggle($(this).text().toLowerCase().includes(q));
        });
    });

    let report_data = [];

    function num_class(val) {
        if (!val || val === 0) return "num-zero";
        if (val >= 10) return "num-high";
        return "num-medium";
    }

    function load_all() {
        const args = {
            from_date: from_date.get_value(),
            to_date: to_date.get_value()
        };

        // Show loading
        $("#team-table-body").html('<div class="ata-loading"><div class="spinner"></div>Loading team data...</div>');
        $("#individual-table-body").html('<div class="ata-loading"><div class="spinner"></div>Loading...</div>');

        frappe.call({
            method: "frappe.desk.query_report.run",
            args: {
                report_name: "Aionion Team Activity Report",
                filters: args
            }
        }).then(res => {
            const result = res.message || {};
            report_data = result.result || [];
            const columns = result.columns || [];

            if (!report_data.length) {
                $("#team-table-body").html('<div class="ata-loading">No data found for this period.</div>');
                $("#individual-table-body").html('<div class="ata-loading">No data found.</div>');
                return;
            }

            // Update summary cards from root-level rows
            const roots = report_data.filter(r => (r.indent || 0) === 0);
            const total_strength  = roots.reduce((s, r) => s + (r.team_strength || 0), 0);
            const total_loggedin  = roots.reduce((s, r) => s + (r.logged_in_count || 0), 0);
            const total_notlogged = roots.reduce((s, r) => s + (r.not_logged_in_count || 0), 0);
            const total_leads_today = roots.reduce((s, r) => s + (r.team_leads_today || 0), 0);
            const total_leads_all   = roots.reduce((s, r) => s + (r.team_total_leads || 0), 0);
            const total_emails      = roots.reduce((s, r) => s + (r.team_emails_today || 0), 0);
            const total_calls       = roots.reduce((s, r) => s + (r.team_calls_today || 0), 0);
            const activity_score    = total_leads_today + total_emails + total_calls;
            const login_pct = total_strength ? Math.round((total_loggedin / total_strength) * 100) : 0;
            const not_pct   = total_strength ? Math.round((total_notlogged / total_strength) * 100) : 0;

            $("#card-strength").text(total_strength);
            $("#card-loggedin").text(total_loggedin);
            $("#card-loggedin-pct").text(login_pct + "% of team");
            $("#card-notloggedin").text(total_notlogged);
            $("#card-notloggedin-pct").text(not_pct + "% of team");
            $("#card-leads-today").text(total_leads_today.toLocaleString());
            $("#card-total-leads").text(total_leads_all.toLocaleString());
            $("#card-emails-today").text(total_emails);
            $("#card-calls-today").text(total_calls);
            $("#card-activity-score").text(activity_score.toLocaleString());

            // Team Hierarchy Table
            const team_html = `
                <table class="ata-table">
                    <thead>
                        <tr>
                            <th>Employee</th>
                            <th>Designation</th>
                            <th>Department</th>
                            <th class="text-center">👥 Strength</th>
                            <th class="text-center">✅ Logged In</th>
                            <th class="text-center">❌ Not In</th>
                            <th class="text-center">📋 Own Leads</th>
                            <th class="text-center">📋 Team Leads</th>
                            <th class="text-center">🗂️ Own Total</th>
                            <th class="text-center">🗂️ Team Total</th>
                            <th class="text-center">✉️ Own Emails</th>
                            <th class="text-center">✉️ Team Emails</th>
                            <th class="text-center">📞 Own Calls</th>
                            <th class="text-center">📞 Team Calls</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${report_data.map(r => {
                            const indent = r.indent || 0;
                            const is_manager = indent === 0;
                            const pad = indent * 24;
                            return `
                            <tr class="${is_manager ? 'manager-row' : ''}">
                                <td style="padding-left:${pad + 12}px;">
                                    ${indent === 0 ? '<span style="margin-right:6px;">🏢</span>' : indent === 1 ? '<span style="margin-right:6px;">👤</span>' : '<span style="margin-right:6px;opacity:0.4;">└</span>'}
                                    <span style="font-weight:${is_manager ? 700 : 400}">${r.employee_name || ""}</span>
                                </td>
                                <td style="color:#64748b;font-size:12px;">${r.designation || "—"}</td>
                                <td style="color:#64748b;font-size:12px;">${r.department || "—"}</td>
                                <td class="text-center"><span class="ata-badge badge-blue">${r.team_strength || 0}</span></td>
                                <td class="text-center"><span class="ata-badge badge-green">${r.logged_in_count || 0}</span></td>
                                <td class="text-center"><span class="ata-badge badge-red">${r.not_logged_in_count || 0}</span></td>
                                <td class="text-center"><span class="${num_class(r.own_leads_today)}">${r.own_leads_today || 0}</span></td>
                                <td class="text-center"><span class="${num_class(r.team_leads_today)}">${r.team_leads_today || 0}</span></td>
                                <td class="text-center">${r.own_total_leads || 0}</td>
                                <td class="text-center"><strong>${r.team_total_leads || 0}</strong></td>
                                <td class="text-center"><span class="${num_class(r.own_emails_today)}">${r.own_emails_today || 0}</span></td>
                                <td class="text-center"><span class="${num_class(r.team_emails_today)}">${r.team_emails_today || 0}</span></td>
                                <td class="text-center"><span class="${num_class(r.own_calls_today)}">${r.own_calls_today || 0}</span></td>
                                <td class="text-center"><span class="${num_class(r.team_calls_today)}">${r.team_calls_today || 0}</span></td>
                            </tr>`;
                        }).join("")}
                    </tbody>
                </table>`;
            $("#team-table-body").html(team_html);

            // Individual View - leaf level employees only
            const individuals = report_data.filter(r => (r.own_leads_today || r.own_total_leads || r.own_emails_today || r.own_calls_today));
            individuals.sort((a, b) => (b.own_leads_today || 0) - (a.own_leads_today || 0));

            const ind_html = `
                <table class="ata-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Employee</th>
                            <th>Department</th>
                            <th class="text-center">📋 Leads Today</th>
                            <th class="text-center">🗂️ Total Leads</th>
                            <th class="text-center">✉️ Emails Today</th>
                            <th class="text-center">📞 Calls Today</th>
                            <th class="text-center">🏆 Score</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${individuals.map((r, i) => {
                            const score = (r.own_leads_today || 0) + (r.own_emails_today || 0) + (r.own_calls_today || 0);
                            const medal = i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : (i + 1);
                            return `
                            <tr>
                                <td class="text-center" style="font-weight:700;color:#64748b;">${medal}</td>
                                <td style="font-weight:500;">${r.employee_name || ""}</td>
                                <td style="color:#64748b;font-size:12px;">${r.department || "—"}</td>
                                <td class="text-center"><span class="${num_class(r.own_leads_today)}">${r.own_leads_today || 0}</span></td>
                                <td class="text-center">${r.own_total_leads || 0}</td>
                                <td class="text-center"><span class="${num_class(r.own_emails_today)}">${r.own_emails_today || 0}</span></td>
                                <td class="text-center"><span class="${num_class(r.own_calls_today)}">${r.own_calls_today || 0}</span></td>
                                <td class="text-center">
                                    <span class="ata-badge ${score > 0 ? 'badge-purple' : 'badge-amber'}">${score}</span>
                                </td>
                            </tr>`;
                        }).join("")}
                    </tbody>
                </table>`;
            $("#individual-table-body").html(ind_html);
        }).catch(err => {
            console.error(err);
            $("#team-table-body").html('<div class="ata-loading">Error loading data. Check console.</div>');
        });
    }

    load_all();
};
