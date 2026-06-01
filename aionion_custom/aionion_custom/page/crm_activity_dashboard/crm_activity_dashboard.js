frappe.pages["crm-activity-dashboard"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "CRM Activity Dashboard",
        single_column: true
    });

    const from_date = page.add_field({
        fieldname: "from_date",
        label: "From Date",
        fieldtype: "Date",
        default: frappe.datetime.month_start(),
        change() { load_dashboard(); load_login_activity(); }
    });

    const to_date = page.add_field({
        fieldname: "to_date",
        label: "To Date",
        fieldtype: "Date",
        default: frappe.datetime.get_today(),
        change() { load_dashboard(); load_login_activity(); }
    });

    $(`
        <style>
            .aion-dash { padding: 20px; font-family: inherit; }

            /* ── Summary Cards ── */
            .aion-stat-card {
                border-radius: 14px;
                padding: 20px 16px;
                text-align: center;
                border: none;
                position: relative;
                overflow: hidden;
            }
            .aion-stat-card .aion-stat-label {
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.8px;
                text-transform: uppercase;
                opacity: 0.75;
                margin-bottom: 6px;
            }
            .aion-stat-card .aion-stat-value {
                font-size: 32px;
                font-weight: 700;
                line-height: 1;
            }
            .aion-stat-card.blue  { background: linear-gradient(135deg,#e0e7ff,#c7d2fe); color:#3730a3; }
            .aion-stat-card.green { background: linear-gradient(135deg,#dcfce7,#bbf7d0); color:#166534; }
            .aion-stat-card.amber { background: linear-gradient(135deg,#fef9c3,#fde68a); color:#92400e; }
            .aion-stat-card.cyan  { background: linear-gradient(135deg,#cffafe,#a5f3fc); color:#155e75; }

            /* ── Tabs ── */
            .aion-tabs {
                display: flex;
                gap: 6px;
                padding: 4px;
                background: #f1f5f9;
                border-radius: 10px;
                margin-bottom: 20px;
                width: fit-content;
            }
            .aion-tab {
                border: none;
                background: transparent;
                padding: 7px 18px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
                color: #64748b;
                cursor: pointer;
                transition: all 0.2s;
            }
            .aion-tab.active {
                background: #fff;
                color: #4361ee;
                box-shadow: 0 1px 4px rgba(0,0,0,0.1);
            }

            /* ── Login Summary Cards ── */
            .aion-login-card {
                border-radius: 14px;
                padding: 18px 20px;
                border: none;
                margin-bottom: 20px;
            }
            .aion-login-card .aion-lc-label {
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.7px;
                text-transform: uppercase;
                margin-bottom: 4px;
            }
            .aion-login-card .aion-lc-value {
                font-size: 28px;
                font-weight: 700;
                line-height: 1.1;
            }
            .aion-login-card .aion-lc-sub {
                font-size: 12px;
                margin-top: 4px;
                opacity: 0.65;
            }
            .aion-progress-bar {
                height: 6px;
                border-radius: 99px;
                background: rgba(0,0,0,0.08);
                margin-top: 10px;
                overflow: hidden;
            }
            .aion-progress-fill {
                height: 100%;
                border-radius: 99px;
                transition: width 0.5s ease;
            }
            .aion-lc-strength { background: linear-gradient(135deg,#e0e7ff,#c7d2fe); color:#3730a3; }
            .aion-lc-login    { background: linear-gradient(135deg,#dcfce7,#bbf7d0); color:#166534; }
            .aion-lc-notlogin { background: linear-gradient(135deg,#fee2e2,#fecaca); color:#991b1b; }

            /* ── Table ── */
            .aion-table { width:100%; border-collapse:separate; border-spacing:0; }
            .aion-table thead th {
                background: #f8fafc;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.6px;
                text-transform: uppercase;
                color: #64748b;
                padding: 10px 12px;
                border-bottom: 2px solid #e2e8f0;
                white-space: nowrap;
            }
            .aion-table tbody tr {
                transition: background 0.15s;
            }
            .aion-table tbody tr:hover { background: #f8fafc; }
            .aion-table tbody td {
                padding: 9px 12px;
                font-size: 13px;
                border-bottom: 1px solid #f1f5f9;
                color: #334155;
                vertical-align: middle;
            }
            .aion-table tbody tr.row-loggedin td:first-child {
                border-left: 3px solid #22c55e;
            }
            .aion-table tbody tr.row-notloggedin td:first-child {
                border-left: 3px solid #f87171;
            }
            .aion-badge {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                padding: 3px 10px;
                border-radius: 99px;
                font-size: 11px;
                font-weight: 600;
            }
            .badge-green { background:#dcfce7; color:#166534; }
            .badge-red   { background:#fee2e2; color:#991b1b; }

            .aion-card-wrap {
                background: #fff;
                border-radius: 14px;
                border: 1px solid #e2e8f0;
                padding: 20px;
                box-shadow: 0 1px 6px rgba(0,0,0,0.04);
            }
        </style>

        <div class="aion-dash">

            <!-- Summary Cards -->
            <div class="row mb-4">
                <div class="col-sm-3 mb-2">
                    <div class="aion-stat-card blue">
                        <div class="aion-stat-label">My Calls</div>
                        <div class="aion-stat-value" id="my-calls">—</div>
                    </div>
                </div>
                <div class="col-sm-3 mb-2">
                    <div class="aion-stat-card green">
                        <div class="aion-stat-label">My Emails</div>
                        <div class="aion-stat-value" id="my-emails">—</div>
                    </div>
                </div>
                <div class="col-sm-3 mb-2">
                    <div class="aion-stat-card amber">
                        <div class="aion-stat-label">Team Calls</div>
                        <div class="aion-stat-value" id="team-calls">—</div>
                    </div>
                </div>
                <div class="col-sm-3 mb-2">
                    <div class="aion-stat-card cyan">
                        <div class="aion-stat-label">Team Emails</div>
                        <div class="aion-stat-value" id="team-emails">—</div>
                    </div>
                </div>
            </div>

            <!-- Tabbed Card -->
            <div class="aion-card-wrap">
                <div class="aion-tabs">
                    <button class="aion-tab active" id="tab-activity">Team Activity Breakdown</button>
                    <button class="aion-tab" id="tab-login">Team Login Activity</button>
                </div>

                <!-- Panel: Activity -->
                <div id="panel-activity">
                    <div id="team-table"><p class="text-muted text-center py-4">Loading...</p></div>
                </div>

                <!-- Panel: Login -->
                <div id="panel-login" style="display:none;">
                    <div class="row mb-3">
                        <div class="col-sm-4 mb-2">
                            <div class="aion-login-card aion-lc-strength">
                                <div class="aion-lc-label">Total Team</div>
                                <div class="aion-lc-value" id="login-total-strength">—</div>
                                <div class="aion-lc-sub">Active employees</div>
                                <div class="aion-progress-bar">
                                    <div class="aion-progress-fill" id="prog-strength" style="width:100%;background:#818cf8;"></div>
                                </div>
                            </div>
                        </div>
                        <div class="col-sm-4 mb-2">
                            <div class="aion-login-card aion-lc-login">
                                <div class="aion-lc-label">Logged In</div>
                                <div class="aion-lc-value" id="login-logged-in">—</div>
                                <div class="aion-lc-sub" id="login-logged-pct">of team today</div>
                                <div class="aion-progress-bar">
                                    <div class="aion-progress-fill" id="prog-login" style="width:0%;background:#22c55e;"></div>
                                </div>
                            </div>
                        </div>
                        <div class="col-sm-4 mb-2">
                            <div class="aion-login-card aion-lc-notlogin">
                                <div class="aion-lc-label">Not Logged In</div>
                                <div class="aion-lc-value" id="login-not-logged-in">—</div>
                                <div class="aion-lc-sub" id="login-notlogged-pct">of team today</div>
                                <div class="aion-progress-bar">
                                    <div class="aion-progress-fill" id="prog-notlogin" style="width:0%;background:#f87171;"></div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div id="login-activity-table"><p class="text-muted text-center py-4">Loading...</p></div>
                </div>
            </div>
        </div>
    `).appendTo(page.main);

    // ── Tab switching ─────────────────────────────────────────────────────────
    $("#tab-activity").on("click", function () {
        $("#panel-activity").show(); $("#panel-login").hide();
        $("#tab-activity").addClass("active"); $("#tab-login").removeClass("active");
    });
    $("#tab-login").on("click", function () {
        $("#panel-activity").hide(); $("#panel-login").show();
        $("#tab-login").addClass("active"); $("#tab-activity").removeClass("active");
    });

    // ── Team Activity Breakdown ───────────────────────────────────────────────
    function load_dashboard() {
        const args = { from_date: from_date.get_value(), to_date: to_date.get_value() };

        Promise.all([
            frappe.call({ method: "aionion_custom.aionion_custom.api.get_call_log_summary", args, async: true }),
            frappe.call({ method: "aionion_custom.aionion_custom.api.get_email_summary", args, async: true })
        ]).then(([call_res, email_res]) => {
            const calls  = call_res.message  || { my_summary: { total: 0 }, team_summary: [] };
            const emails = email_res.message || { my_summary: { total_sent: 0 }, team_summary: [] };

            $("#my-calls").text(calls.my_summary.total || 0);
            $("#my-emails").text(emails.my_summary.total_sent || 0);

            const team_call_total  = calls.team_summary.reduce((s, r) => s + (r.total_calls || 0), 0);
            const team_email_total = emails.team_summary.reduce((s, r) => s + (r.total_sent  || 0), 0);
            $("#team-calls").text(team_call_total);
            $("#team-emails").text(team_email_total);

            const user_map = {};
            calls.team_summary.forEach(r => {
                user_map[r.user] = { full_name: r.full_name, roles: r.roles, calls: r.total_calls || 0, emails: 0, is_me: r.is_me };
            });
            emails.team_summary.forEach(r => {
                if (user_map[r.user]) {
                    user_map[r.user].emails = r.total_sent || 0;
                } else {
                    user_map[r.user] = { full_name: r.full_name, roles: r.roles, calls: 0, emails: r.total_sent || 0, is_me: r.is_me };
                }
            });

            const rows = Object.values(user_map).sort((a, b) => (b.calls + b.emails) - (a.calls + a.emails));

            if (!rows.length) {
                $("#team-table").html(`<p class="text-muted text-center py-4">No activity data for this period.</p>`);
                return;
            }

            $("#team-table").html(`
                <table class="aion-table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Role</th>
                            <th class="text-center">📞 Calls</th>
                            <th class="text-center">✉️ Emails</th>
                            <th class="text-center">Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows.map(r => `
                            <tr style="${r.is_me ? 'background:#eff6ff;' : ''}">
                                <td style="font-weight:${r.is_me ? '700' : '400'}">
                                    ${r.full_name}
                                    ${r.is_me ? '<span class="aion-badge badge-green ml-1">Me</span>' : ''}
                                </td>
                                <td style="color:#64748b;">${(r.roles || ["Agent"]).join(", ")}</td>
                                <td class="text-center font-weight-bold">${r.calls}</td>
                                <td class="text-center font-weight-bold">${r.emails}</td>
                                <td class="text-center">
                                    <span class="aion-badge badge-green">${r.calls + r.emails}</span>
                                </td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            `);
        });
    }

    // ── Team Login Activity (hierarchy-scoped) ────────────────────────────────
    function load_login_activity() {
        const is_admin = frappe.user_roles.includes("System Manager")
                      || frappe.session.user === "Administrator";

        // Step 1: get current user's Employee code (skip fetch for admin)
        const get_emp = is_admin
            ? Promise.resolve(null)
            : frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype:   "Employee",
                    filters:   { user_id: frappe.session.user, status: "Active" },
                    fieldname: "name"
                }
              });

        get_emp.then(emp_res => {
            const emp_code = emp_res && emp_res.message && emp_res.message.name;

            // Step 2: scope non-admins to their own subtree via top_level_manager
            const report_filters = {
                from_date: from_date.get_value(),
                to_date:   to_date.get_value()
            };
            if (!is_admin && emp_code) {
                report_filters.top_level_manager = emp_code;
            }

            // Step 3: run the report with scoped filters
            frappe.call({
                method: "frappe.desk.query_report.run",
                args: { report_name: "Team Login Activity", filters: report_filters },
                async: true
            }).then(res => {
                const rows = (res.message && res.message.result) || [];

                if (!rows.length) {
                    $("#login-activity-table").html(`<p class="text-muted text-center py-4">No login data for this period.</p>`);
                    $("#login-total-strength").text(0);
                    $("#login-logged-in").text("0 / 0");
                    $("#login-not-logged-in").text("0 / 0");
                    return;
                }

                // Summary cards
                const total     = rows.length;
                const loggedIn  = rows.filter(r => (r.login_status||"").includes("Logged In") && !(r.login_status||"").includes("Not")).length;
                const notLogged = total - loggedIn;
                const loginPct  = total ? Math.round((loggedIn  / total) * 100) : 0;
                const notPct    = total ? Math.round((notLogged / total) * 100) : 0;

                $("#login-total-strength").text(total);
                $("#login-logged-in").text(`${loggedIn} / ${total}`);
                $("#login-not-logged-in").text(`${notLogged} / ${total}`);
                $("#login-logged-pct").text(`${loginPct}% of team today`);
                $("#login-notlogged-pct").text(`${notPct}% of team today`);
                $("#prog-login").css("width", loginPct + "%");
                $("#prog-notlogin").css("width", notPct + "%");

                // Table
                $("#login-activity-table").html(`
                    <table class="aion-table">
                        <thead>
                            <tr>
                                <th>Employee</th>
                                <th>Designation</th>
                                <th>Reports To</th>
                                <th class="text-center">Team Strength</th>
                                <th class="text-center">Logged In</th>
                                <th class="text-center">Not Logged In</th>
                                <th class="text-center">Status</th>
                                <th>First Login</th>
                                <th>Last Logout</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows.map(r => {
                                const isIn  = (r.login_status||"").includes("Logged In") && !(r.login_status||"").includes("Not");
                                const badge = isIn
                                    ? `<span class="aion-badge badge-green">✅ Logged In</span>`
                                    : `<span class="aion-badge badge-red">❌ Not Logged In</span>`;
                                return `
                                <tr class="${isIn ? 'row-loggedin' : 'row-notloggedin'}">
                                    <td style="padding-left:${((r.indent||0)*20)+8}px;font-weight:500;">${r.employee_name||""}</td>
                                    <td style="color:#64748b;">${r.designation||"—"}</td>
                                    <td style="color:#64748b;">${r.reports_to_name||"—"}</td>
                                    <td class="text-center">${r.team_strength||"—"}</td>
                                    <td class="text-center">${r.logged_in_count||"—"}</td>
                                    <td class="text-center">${r.not_logged_in_count||"—"}</td>
                                    <td class="text-center">${badge}</td>
                                    <td style="font-size:12px;color:#64748b;">${r.first_login||"—"}</td>
                                    <td style="font-size:12px;color:#64748b;">${r.last_logout||"—"}</td>
                                </tr>`;
                            }).join("")}
                        </tbody>
                    </table>
                `);
            }).catch(() => {
                $("#login-activity-table").html(`<p class="text-muted text-center py-4">Could not load login activity.</p>`);
            });
        });
    }

    // ── Initial load ──────────────────────────────────────────────────────────
    load_dashboard();
    load_login_activity();
};