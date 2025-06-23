const superMatrizId = "{{ super_matriz.id }}";
const socket = new WebSocket("ws://" + window.location.host + "/ws/validates/" + superMatrizId + "/");

socket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === "estado_actualizado") {
        const validateId = data.validate_id;
        const nuevoEstado = data.nuevo_estado;
        const celda = document.querySelector(`#estado-validate-${validateId}`);
        if (celda) {
            const select = celda.querySelector('select');
            if (select && select.value !== nuevoEstado) {
                select.value = nuevoEstado;
                aplicarColorEstado(select);
                select.classList.add("flash-update");
                setTimeout(() => select.classList.remove("flash-update"), 1500);
            }
        }
    }
};

document.querySelectorAll("select").forEach(select => {
    select.classList.add("form-select", "form-select-sm", "estado-input");
    aplicarColorEstado(select);
    select.addEventListener("change", function() {
        const tr = this.closest("tr");
        const validateId = tr.dataset.id;
        const nuevoEstado = this.value;

        fetch("{% url 'matrix_app:actualizar_estado_validate' %}", {
            method: "POST",
            headers: {
                "X-CSRFToken": "{{ csrf_token }}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            body: `validate_id=${validateId}&nuevo_estado=${nuevoEstado}`
        });

        aplicarColorEstado(this);
    });
});

function aplicarColorEstado(select) {
    const estado = select.value.toLowerCase().trim();
    select.className = "form-select form-select-sm estado-input";

    if (estado === "funciona") {
        select.classList.add("bg-success", "text-white");
    } else if (estado === "falla_nueva") {
        select.classList.add("bg-danger", "text-white");
    } else if (estado === "falla_persistente") {
        select.style.backgroundColor = "#ef9a9a";
        select.style.color = "#000";
    } else if (estado === "n/a") {
        select.classList.add("bg-secondary", "text-dark");
    } else if (estado === "pendiente") {
        select.style.backgroundColor = "#ffcc80";
        select.style.color = "#000";
    } else if (estado === "por_ejecutar") {
        select.classList.add("bg-warning", "text-dark");
    } else {
        select.style.backgroundColor = "#90caf9";
        select.style.color = "#000";
    }

    select.style.padding = "8px 14px";
    select.style.height = "40px";
    select.style.fontWeight = "bold";
}

// Filtro por tester
document.querySelectorAll(".filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        const tester = btn.dataset.tester;
        document.querySelectorAll("#validates-table tbody tr").forEach(row => {
            if (tester === "all" || row.dataset.tester === tester) {
                row.style.display = "";
            } else {
                row.style.display = "none";
            }
        });
    });
});