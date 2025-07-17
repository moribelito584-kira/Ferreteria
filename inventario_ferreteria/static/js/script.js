// inventario_ferreteria/static/js/script.js
document.addEventListener('DOMContentLoaded', function() {
    const deleteForms = document.querySelectorAll('.delete-form');
    deleteForms.forEach(form => {
        form.addEventListener('submit', function(event) {
            const confirmDelete = confirm('¿Estás seguro de que quieres eliminar este producto? Esta acción es irreversible.');
            if (!confirmDelete) {
                event.preventDefault();
            }
        });
    });

    const flashMessages = document.querySelector('.flashes');
    if (flashMessages) {
        setTimeout(() => {
            flashMessages.style.transition = 'opacity 0.5s ease-out';
            flashMessages.style.opacity = '0';
            setTimeout(() => flashMessages.remove(), 500);
        }, 5000);
    }
});