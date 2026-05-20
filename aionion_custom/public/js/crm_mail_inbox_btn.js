(function() {
    // Inject CSS immediately to hide Assign To elements before Vue renders
    var style = document.createElement('style');
    style.id = 'aion-assign-hide';
    style.textContent = [
        'div.relative.inline-block.shrink-0.w-6.h-6.rounded-full { display: none !important; }'
    ].join('');
    document.head.appendChild(style);

    // After frappe loads, check if manager and re-show
    function checkManagerRole() {
        if (typeof frappe === 'undefined' || !frappe.call) {
            setTimeout(checkManagerRole, 500);
            return;
        }
        frappe.call({
            method: 'aionion_custom.aionion_custom.controllers.crm_lead.get_current_user_roles',
            callback: function(r) {
                var roles = r.message || [];
                var managerRoles = ['Insurance Sales Manager','Insurance Renewals Manager',
                    'US Subscription Admin','Capital Manager','Global RM Manager',
                    'System Manager','Administrator'];
                var isManager = roles.some(function(r) {
                    return managerRoles.indexOf(r) !== -1;
                });
                if (isManager) {
                    var s = document.getElementById('aion-assign-hide');
                    if (s) s.remove();
                }
            }
        });
    }
    setTimeout(checkManagerRole, 1000);
})();

(function() {
    var BTN_CLASS = 'inline-flex items-center justify-center gap-2 transition-colors focus:outline-none shrink-0 text-ink-gray-8 bg-surface-gray-2 hover:bg-surface-gray-3 active:bg-surface-gray-4 focus-visible:ring focus-visible:ring-outline-gray-3 h-7 text-base px-2 rounded mail-inbox-crm-btn';

    function addMailInboxBtn() {
        if (!window.location.href.includes('/crm/leads')) return false;
        if (document.querySelector('.mail-inbox-crm-btn')) return true;

        var allButtons = document.querySelectorAll('button');
        var targetContainer = null;
        var customersBtn = null;

        allButtons.forEach(function(btn) {
            if (btn.textContent.trim() === 'Customers') {
                targetContainer = btn.parentElement;
                customersBtn = btn;
            }
        });

        if (!targetContainer || !customersBtn) return false;

        var btn = document.createElement('button');
        btn.textContent = 'Mail Inbox';
        btn.className = BTN_CLASS;
        btn.onclick = function() {
            window.open('/desk/crm-mail-inbox', '_blank');
        };

        targetContainer.insertBefore(btn, customersBtn);
        return true;
    }

    function tryAdd(attempts) {
        if (attempts <= 0) return;
        if (!addMailInboxBtn()) {
            setTimeout(function() { tryAdd(attempts - 1); }, 500);
        }
    }

    var lastUrl = location.href;
    new MutationObserver(function() {
        var url = location.href;
        if (url !== lastUrl) {
            lastUrl = url;
            setTimeout(function() { tryAdd(10); }, 300);
        }
    }).observe(document, {subtree: true, childList: true});

    setTimeout(function() { tryAdd(10); }, 500);
})();
