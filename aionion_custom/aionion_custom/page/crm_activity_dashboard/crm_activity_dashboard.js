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
        change() { load_dashboard(); }
    });

    const to_date = page.add_field({
        fieldname: "to_date",
        label: "To Date",
        fieldtype: "Date",
        default: frappe.datetime.get_today(),
        change() { load_dashboard(); }
    });

    $(` <div class="crm-dashboard p-4">
            <div class="row mb-4" id="summary-cards">
                <div class="col-sm-3">
                    <div class="card shadow-sm text-center p-3">
                        <div class="text-muted small">My Calls</div>
                        <div class="h2 font-weight-bold text-primary" id="my-calls">—</div>
                    </div>
                </div>
                <div class="col-sm-3">
                    <div class="card shadow-sm text-center p-3">
                        <div class="text-muted small">My Emails</div>
                        <div class="h2 font-weight-bold text-success" id="my-emails">—</div>
                    </div>
                </div>
                <div class="col-sm-3">
                    <div class="card shadow-sm text-center p-3">
                        <div class="text-muted small">Team Calls</div>
                        <div class="h2 font-weight-bold text-warning" id="team-calls">—</div>
                    </div>
                </div>
                <div class="col-sm-3">
                    <div class="card shadow-sm text-center p-3">
                        <div class="text-muted small">Team Emails</div>
                        <div class="h2 font-weight-bold text-info" id="team-emails">—</div>
                    </div>
                </div>
            </div>
            <div class="card shadow-sm p-3">
                <h6 class="mb-3">Team Activity Breakdown</h6>
                <div id="team-table"><p class="text-muted">Loading...</p></div>
            </div>
        </div>
    `).appendTo(page.main);

    function load_dashboard() {
        const args = {
            from_date: from_date.get_value(),
            to_date: to_date.get_value()
        };

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
                $("#team-table").html(`<p class="text-muted text-center">No activity data for this period.</p>`);
                return;
            }

            $("#team-table").html(`
                <table class="table table-bordered table-hover">
                    <thead class="thead-light">
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
                            <tr class="${r.is_me ? 'table-primary font-weight-bold' : ''}">
                                <td>${r.full_name} ${r.is_me ? '<span class="badge badge-primary">Me</span>' : ''}</td>
                                <td>${(r.roles || ["Agent"]).join(", ")}</td>
                                <td class="text-center">${r.calls}</td>
                                <td class="text-center">${r.emails}</td>
                                <td class="text-center font-weight-bold">${r.calls + r.emails}</td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            `);
        });
    }

    load_dashboard();
};
