// Handle dashboard/home shortcut taps while offline by queueing a POST
// through the existing offline form interceptor.
(function () {
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function parseQty(input) {
        const n = parseFloat(String(input || '').trim());
        if (!Number.isFinite(n) || n <= 0) return null;
        return n;
    }

    document.addEventListener('click', function (event) {
        const link = event.target.closest('.js-shortcut-link');
        if (!link) return;
        if (navigator.onLine) return;

        event.preventDefault();

        const shortcutName = link.getAttribute('data-shortcut-name') || 'Shortcut';
        const qtyText = window.prompt('Offline mode: enter quantity for ' + shortcutName, '1');
        if (qtyText === null) return;

        const qty = parseQty(qtyText);
        if (!qty) {
            window.alert('Please enter a valid quantity greater than 0.');
            return;
        }

        const form = document.createElement('form');
        form.method = 'POST';
        form.action = link.href;
        form.id = 'offline_shortcut_form';
        form.style.display = 'none';

        const csrf = document.createElement('input');
        csrf.type = 'hidden';
        csrf.name = 'csrfmiddlewaretoken';
        csrf.value = getCookie('csrftoken') || '';

        const quantity = document.createElement('input');
        quantity.type = 'hidden';
        quantity.name = 'quantity';
        quantity.value = String(qty);

        const note = document.createElement('input');
        note.type = 'hidden';
        note.name = 'note';
        note.value = '';

        form.appendChild(csrf);
        form.appendChild(quantity);
        form.appendChild(note);
        document.body.appendChild(form);

        if (typeof setupOfflineForm === 'function') {
            setupOfflineForm('offline_shortcut_form');
            form.requestSubmit();
        } else {
            window.alert('Offline form handler is not available. Please try again.');
            form.remove();
        }
    });
})();
