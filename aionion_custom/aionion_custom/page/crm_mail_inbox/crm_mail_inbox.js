frappe.pages['crm-mail-inbox'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Mail Inbox',
        single_column: true
    });

    $(wrapper).find('.page-content').html(`
        <div style="padding:20px">
            <div style="display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:15px">
                <select id="inbox-filter" class="form-control" style="width:150px">
                    <option value="Received">Incoming</option>
                    <option value="Sent">Sent</option>
                </select>
                <input type="text" id="inbox-subject-search" class="form-control"
                    placeholder="Search by subject..." style="width:250px"/>
                <input type="date" id="inbox-from-date" class="form-control" style="width:160px" title="From Date"/>
                <input type="date" id="inbox-to-date" class="form-control" style="width:160px" title="To Date"/>
                <button class="btn btn-sm btn-primary" onclick="loadInbox()">Search</button>
                <button class="btn btn-sm btn-default" onclick="clearFilters()">Clear</button>
            </div>
            <div id="mail-inbox-list"><p class="text-muted">Loading...</p></div>
        </div>
    `);

    document.getElementById('inbox-from-date').value = frappe.datetime.month_start();
    document.getElementById('inbox-to-date').value = frappe.datetime.get_today();

    var searchTimer;
    document.getElementById('inbox-subject-search').addEventListener('input', function() {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(function() { loadInbox(); }, 400);
    });

    document.getElementById('inbox-filter').addEventListener('change', function() { loadInbox(); });

    window.clearFilters = function() {
        document.getElementById('inbox-subject-search').value = '';
        document.getElementById('inbox-from-date').value = frappe.datetime.month_start();
        document.getElementById('inbox-to-date').value = frappe.datetime.get_today();
        document.getElementById('inbox-filter').value = 'Received';
        loadInbox();
    };

    window.loadInbox = function() {
        var type      = document.getElementById('inbox-filter').value;
        var subject   = (document.getElementById('inbox-subject-search').value || '').trim();
        var from_date = document.getElementById('inbox-from-date').value;
        var to_date   = document.getElementById('inbox-to-date').value;

        document.getElementById('mail-inbox-list').innerHTML = '<p class="text-muted">Loading...</p>';

        var filters = {
            reference_doctype: 'CRM Lead',
            sent_or_received: type,
            communication_medium: 'Email'
        };

        if (subject) filters['subject'] = ['like', '%' + subject + '%'];
        if (from_date && to_date) {
            filters['creation'] = ['between', [from_date, to_date + ' 23:59:59']];
        } else if (from_date) {
            filters['creation'] = ['>=', from_date];
        }

        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Communication',
                filters: filters,
                fields: ['name','sender','sender_full_name','recipients','subject','reference_name','creation'],
                order_by: 'creation desc',
                limit: 100
            },
            callback: function(r) {
                var data = r.message || [];
                var label = type === 'Received' ? 'From' : 'To';
                var html = `
                    <div style="margin-bottom:8px;color:#888;font-size:12px">${data.length} email(s) found</div>
                    <table class="table table-bordered table-hover">
                        <thead style="background:#f5f5f5">
                            <tr><th>${label}</th><th>Subject</th><th>Lead</th><th>Time</th></tr>
                        </thead><tbody>`;

                if (!data.length) {
                    html += '<tr><td colspan="4" class="text-center text-muted">No emails found</td></tr>';
                }
                data.forEach(function(row) {
                    var person = type === 'Received'
                        ? (row.sender_full_name || row.sender || '-')
                        : (row.recipients || '-');
                    html += `<tr style="cursor:pointer" onclick="window.location.href='/crm/leads/${row.reference_name}'">
                        <td>${person}</td>
                        <td>${row.subject || '-'}</td>
                        <td><b>${row.reference_name || '-'}</b></td>
                        <td>${frappe.datetime.prettyDate(row.creation)}</td>
                    </tr>`;
                });
                html += '</tbody></table>';
                document.getElementById('mail-inbox-list').innerHTML = html;
            }
        });
    };

    loadInbox();
};
