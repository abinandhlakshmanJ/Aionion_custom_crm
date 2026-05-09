frappe.pages["call-log-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Call Log Dashboard",
		single_column: true,
	});

	// ── Date filters in toolbar ───────────────────────────────────────
	const from_field = page.add_field({
		fieldtype: "Date",
		fieldname: "from_date",
		label: "From Date",
		default: frappe.datetime.month_start(),
		change() { load_dashboard(); },
	});

	const to_field = page.add_field({
		fieldtype: "Date",
		fieldname: "to_date",
		label: "To Date",
		default: frappe.datetime.get_today(),
		change() { load_dashboard(); },
	});

	// ── Inject HTML skeleton into page.body (already a jQuery object) ─
	page.body.html(`
		<div id="cld-dashboard" style="padding:20px;">

			<div id="cld-kpis" style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:24px;">
				<div class="frappe-card" style="flex:1;padding:20px;text-align:center;">
					<div style="color:var(--text-muted);font-size:13px;">Loading...</div>
				</div>
			</div>

			<div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:24px;">
				<div class="frappe-card" style="flex:1;min-width:320px;padding:16px;">
					<h6 style="margin-bottom:12px;color:var(--text-muted);">Incoming vs Outgoing</h6>
					<canvas id="cld-type-chart" height="180"></canvas>
				</div>
				<div class="frappe-card" style="flex:1;min-width:260px;padding:16px;">
					<h6 style="margin-bottom:12px;color:var(--text-muted);">Call Status Split</h6>
					<canvas id="cld-status-chart" height="180"></canvas>
				</div>
			</div>

			<div class="frappe-card" style="padding:16px;margin-bottom:24px;">
				<h6 style="margin-bottom:12px;color:var(--text-muted);">Team Leaderboard (HRMS Hierarchy)</h6>
				<div id="cld-leaderboard"><div style="color:var(--text-muted);">Loading...</div></div>
			</div>

			<div class="frappe-card" style="padding:16px;">
				<h6 style="margin-bottom:12px;color:var(--text-muted);">Org Chart – Call Volume</h6>
				<div id="cld-org-tree" style="overflow-x:auto;"><div style="color:var(--text-muted);">Loading...</div></div>
			</div>
		</div>
	`);

	// ── Load Chart.js first, then load data ───────────────────────────
	if (window.Chart) {
		load_dashboard();
	} else {
		frappe.require(
			"https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js",
			function () { load_dashboard(); }
		);
	}

	let type_chart_instance, status_chart_instance;

	// ── Main loader ───────────────────────────────────────────────────
	function load_dashboard() {
		const from_date = from_field.get_value();
		const to_date   = to_field.get_value();

		frappe.call({
			method: "aionion_custom.api.call_log_dashboard.get_call_log_summary",
			args: { from_date, to_date },
			callback(r) {
				if (r.message) render_kpis(r.message);
			},
		});

		frappe.call({
			method: "aionion_custom.api.call_log_dashboard.get_calls_per_employee",
			args: { from_date, to_date },
			callback(r) {
				if (r.message) {
					render_leaderboard(r.message);
					frappe.call({
						method: "aionion_custom.api.call_log_dashboard.get_hrms_hierarchy",
						callback(hr) {
							if (hr.message) render_org_tree(hr.message, r.message);
						},
					});
				}
			},
		});
	}

	// ── KPI Cards ─────────────────────────────────────────────────────
	function render_kpis(data) {
		const cards = [
			{ label: "Total Calls", value: data.total,     color: "#5e64ff", icon: "📞" },
			{ label: "Incoming",    value: data.incoming,  color: "#28a745", icon: "↙️" },
			{ label: "Outgoing",    value: data.outgoing,  color: "#007bff", icon: "↗️" },
			{ label: "Missed",      value: data.missed,    color: "#dc3545", icon: "❌" },
			{ label: "Completed",   value: data.completed, color: "#17a2b8", icon: "✅" },
		];

		const html = cards.map(c => `
			<div class="frappe-card" style="flex:1;min-width:140px;padding:16px;
				border-top:3px solid ${c.color};text-align:center;">
				<div style="font-size:22px;">${c.icon}</div>
				<div style="font-size:28px;font-weight:700;color:${c.color};">${c.value}</div>
				<div style="font-size:12px;color:var(--text-muted);margin-top:4px;">${c.label}</div>
			</div>
		`).join("");

		page.body.find("#cld-kpis").html(html);
		render_charts(data);
	}

	// ── Charts ────────────────────────────────────────────────────────
	function render_charts(data) {
		if (!window.Chart) return;

		const type_ctx = page.body.find("#cld-type-chart")[0];
		if (type_chart_instance) type_chart_instance.destroy();
		type_chart_instance = new Chart(type_ctx, {
			type: "bar",
			data: {
				labels: ["Incoming", "Outgoing"],
				datasets: [{
					label: "Calls",
					data: [data.incoming, data.outgoing],
					backgroundColor: ["#28a745", "#007bff"],
					borderRadius: 6,
				}],
			},
			options: {
				plugins: { legend: { display: false } },
				scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
			},
		});

		const status_ctx = page.body.find("#cld-status-chart")[0];
		if (status_chart_instance) status_chart_instance.destroy();
		status_chart_instance = new Chart(status_ctx, {
			type: "doughnut",
			data: {
				labels: ["Completed", "Missed"],
				datasets: [{
					data: [data.completed, data.missed],
					backgroundColor: ["#17a2b8", "#dc3545"],
				}],
			},
			options: {
				cutout: "65%",
				plugins: { legend: { position: "bottom" } },
			},
		});
	}

	// ── Leaderboard ───────────────────────────────────────────────────
	function render_leaderboard(employees) {
		if (!employees.length) {
			page.body.find("#cld-leaderboard").html(
				'<p style="color:var(--text-muted);">No data found.</p>'
			);
			return;
		}

		const sorted = [...employees].sort((a, b) => b.total - a.total);
		const max    = sorted[0].total || 1;

		const rows = sorted.map((e, i) => `
			<tr>
				<td style="padding:8px 4px;">${i + 1}</td>
				<td style="padding:8px 4px;">
					${e.image
						? `<img src="${e.image}" style="width:28px;height:28px;border-radius:50%;
							 object-fit:cover;margin-right:6px;" />`
						: ""}
					<b>${e.employee_name || e.user_id}</b>
					<div style="font-size:11px;color:var(--text-muted);">${e.designation || ""}</div>
				</td>
				<td style="padding:8px 4px;color:var(--text-muted);font-size:12px;">
					${e.reports_to || "—"}
				</td>
				<td style="padding:8px 4px;text-align:center;">
					<span style="background:#28a74522;color:#28a745;padding:2px 8px;
						border-radius:12px;">${e.incoming} ↙</span>
				</td>
				<td style="padding:8px 4px;text-align:center;">
					<span style="background:#007bff22;color:#007bff;padding:2px 8px;
						border-radius:12px;">${e.outgoing} ↗</span>
				</td>
				<td style="padding:8px 4px;text-align:center;font-weight:700;">${e.total}</td>
				<td style="padding:8px 4px;min-width:120px;">
					<div style="background:var(--border-color);border-radius:4px;
						height:8px;overflow:hidden;">
						<div style="background:#5e64ff;
							width:${Math.round((e.total / max) * 100)}%;height:100%;"></div>
					</div>
				</td>
			</tr>
		`).join("");

		page.body.find("#cld-leaderboard").html(`
			<table style="width:100%;border-collapse:collapse;">
				<thead>
					<tr style="font-size:12px;color:var(--text-muted);
						border-bottom:1px solid var(--border-color);">
						<th style="padding:8px 4px;">#</th>
						<th style="padding:8px 4px;">Agent</th>
						<th style="padding:8px 4px;">Reports To</th>
						<th style="padding:8px 4px;text-align:center;">Incoming</th>
						<th style="padding:8px 4px;text-align:center;">Outgoing</th>
						<th style="padding:8px 4px;text-align:center;">Total</th>
						<th style="padding:8px 4px;">Share</th>
					</tr>
				</thead>
				<tbody>${rows}</tbody>
			</table>
		`);
	}

	// ── Org Tree ──────────────────────────────────────────────────────
	function render_org_tree(hierarchy, call_data) {
		const call_map = {};
		call_data.forEach(e => { call_map[e.employee] = e; });

		const children_map = {};
		const all_ids = new Set(hierarchy.map(e => e.name));

		hierarchy.forEach(e => {
			const parent = (e.reports_to && all_ids.has(e.reports_to))
				? e.reports_to
				: "__root__";
			if (!children_map[parent]) children_map[parent] = [];
			children_map[parent].push(e);
		});

		function render_node(emp, depth) {
			const calls    = call_map[emp.name] || { incoming: 0, outgoing: 0, total: 0 };
			const indent   = depth * 28;
			const children = children_map[emp.name] || [];

			const node_html = `
				<div style="display:flex;align-items:flex-start;margin:4px 0;
					margin-left:${indent}px;">
					${children.length
						? `<span style="margin-right:6px;color:var(--text-muted);
							 font-size:12px;margin-top:2px;">▼</span>`
						: `<span style="margin-right:6px;width:12px;display:inline-block;"></span>`}
					<div class="frappe-card" style="padding:10px 14px;display:inline-flex;
						align-items:center;gap:10px;min-width:260px;">
						${emp.image
							? `<img src="${emp.image}" style="width:32px;height:32px;
								 border-radius:50%;object-fit:cover;" />`
							: `<div style="width:32px;height:32px;border-radius:50%;
								 background:var(--bg-color);display:flex;align-items:center;
								 justify-content:center;font-size:14px;">👤</div>`}
						<div>
							<div style="font-weight:600;font-size:13px;">${emp.employee_name}</div>
							<div style="font-size:11px;color:var(--text-muted);">
								${emp.designation || ""}
							</div>
						</div>
						<div style="margin-left:auto;display:flex;gap:8px;font-size:12px;">
							<span style="background:#28a74522;color:#28a745;padding:2px 8px;
								border-radius:12px;">↙ ${calls.incoming}</span>
							<span style="background:#007bff22;color:#007bff;padding:2px 8px;
								border-radius:12px;">↗ ${calls.outgoing}</span>
						</div>
					</div>
				</div>
			`;
			return node_html + children.map(c => render_node(c, depth + 1)).join("");
		}

		const roots    = children_map["__root__"] || [];
		const tree_html = roots.map(r => render_node(r, 0)).join("");

		page.body.find("#cld-org-tree").html(
			tree_html || '<p style="color:var(--text-muted);">No employee hierarchy found.</p>'
		);
	}
};