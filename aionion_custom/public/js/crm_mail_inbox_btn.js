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
