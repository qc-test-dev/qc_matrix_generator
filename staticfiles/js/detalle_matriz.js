const matrizId = "{{ matriz.id }}";
    const socket = new WebSocket("ws://" + window.location.host + "/ws/matriz/" + matrizId + "/");

    socket.onopen = () => console.log("WebSocket conectado.");
    socket.onerror = e => console.error("WebSocket error:", e);

    socket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        const casoId = data.caso_id;

        if (data.tipo === 'estado') {
            const nuevoEstado = data.valor;
            const celdaEstado = document.querySelector(`#estado-caso-${casoId}`);
            if (celdaEstado) {
                const select = celdaEstado.querySelector('select');
                if (select && select.value !== nuevoEstado) {
                    select.value = nuevoEstado;
                    aplicarColorEstado(select);
                    select.classList.add("flash-update");
                    setTimeout(() => select.classList.remove("flash-update"), 1500);
                }
            }
        }

        if (data.tipo === 'nota') {
            const nuevaNota = data.valor;
            const celdaNota = document.querySelector(`#nota-caso-${casoId}`);
            if (celdaNota) {
                const input = celdaNota.querySelector('input');
                if (input && input.value !== nuevaNota) {
                    input.value = nuevaNota;
                    input.classList.add("flash-update");
                    setTimeout(() => input.classList.remove("flash-update"), 1500);
                }
            }
        }
    };

    document.querySelectorAll('.estado-input').forEach(select => {
        aplicarColorEstado(select);
        select.addEventListener('change', function () {
            const casoId = this.closest('tr').dataset.id;
            const nuevoEstado = this.value;

            fetch("{% url 'matrix_app:actualizar_estado_caso' %}", {
                method: "POST",
                headers: {
                    "X-CSRFToken": "{{ csrf_token }}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                body: `caso_id=${casoId}&nuevo_estado=${nuevoEstado}`
            });

            aplicarColorEstado(this);
        });
    });

    document.querySelectorAll('.nota-input').forEach(input => {
        input.addEventListener('blur', function () {
            const casoId = this.closest('tr').dataset.id;
            const nuevaNota = this.value;

            fetch("{% url 'matrix_app:actualizar_nota_caso' %}", {
                method: "POST",
                headers: {
                    "X-CSRFToken": "{{ csrf_token }}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                body: `caso_id=${casoId}&nota=${encodeURIComponent(nuevaNota)}`
            });
        });
    });

    function aplicarColorEstado(select) {
        const estado = select.value.toLowerCase().trim();
        select.className = "estado-input form-control";

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