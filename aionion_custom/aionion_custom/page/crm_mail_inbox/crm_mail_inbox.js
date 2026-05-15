frappe.pages['crm-mail-inbox'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Mail Inbox',
        single_column: true
    });

    $(wrapper).find('.page-content').html(`
        <div style="padding:20px">
            <select id="inbox-filter" class="form-control" style="width:200px;display:inline-block;margin-bottom:15px">
                <option value="Received">Incoming</option>
                <option value="Sent">Sent</option>
            </select>
            <button class="btn btn-sm btn-default" style="margin-left:8px" onclick="loadInbox()">Refresh</button>
            <div id="mail-inbox-list"></div>
        </div>
    `);

    window.loadInbox = function() {
        var type = document.getElementById('inbox-filter').value;
        document.getElementById('mail-inbox-list').innerHTML = '<p class="text-muted">Loading...</p>';

        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Communication',
                filters: {reference_doctype: 'CRM Lead', sent_or_received: type, communication_medium: 'Email'},
                fields: ['name','sender','sender_full_name','subject','reference_name','creation'],
                order_by: 'creation desc',
                limit: 50
            },
            callback: function(r) {
                var data = r.message || [];
                var html = '<table class="table table-bordered table-hover"><thead style="background:#f5f5f5"><tr><th>From/To</th><th>Subject</th><th>Lead</th><th>Time</th></tr></thead><tbody>';
                if (!data.length) html += '<tr><td colspan="4" class="text-center text-muted">No emails found</td></tr>';
                data.forEach(function(row) {
                    html += `<tr style="cursor:pointer" onclick="window.location.href='/crm/leads/${row.reference_name}'">
                        <td>${row.sender_full_name || row.sender || '-'}</td>
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
}
