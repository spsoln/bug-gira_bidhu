// Show the Application and Product fields only when the ticket type is Bug.
(function () {
    var typeSelect = document.getElementById('id_ticket_type');
    if (!typeSelect) return;

    var bugOnlyGroups = document.querySelectorAll(
        '[data-field="application"], [data-field="product"]'
    );

    function sync() {
        var isBug = typeSelect.value === 'bug';
        bugOnlyGroups.forEach(function (group) {
            group.hidden = !isBug;
        });
    }

    typeSelect.addEventListener('change', sync);
    sync();  // set the correct state on page load
})();