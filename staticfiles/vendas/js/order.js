// ==============================
// Confirmação de pedido
// ==============================
document.addEventListener("DOMContentLoaded", function () {
    const confirmModal = document.getElementById("confirmOrderModal");
    let confirmOrderPk = null;

    if (confirmModal) {
        confirmModal.addEventListener("show.bs.modal", function (event) {
            const button = event.relatedTarget;
            confirmOrderPk = button.getAttribute("data-id");
            const number = button.getAttribute("data-number");
            const client = button.getAttribute("data-client");

            document.getElementById("confirmOrderNumber").textContent = number;
            document.getElementById("confirmOrderClient").textContent = client;

            const btn = document.getElementById("confirmOrderBtn");
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Confirmar';
        });

        document.getElementById("confirmOrderBtn").addEventListener("click", function () {
            if (!confirmOrderPk) return;

            const btn = this;
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Salvando...';

            fetch(`/vendas/orders/${confirmOrderPk}/confirm/`, {
                method: "POST",
                headers: {
                    "X-CSRFToken": document.cookie.match(/csrftoken=([^;]+)/)?.[1] ?? "",
                },
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    const statusCell = document.getElementById(`order-status-${confirmOrderPk}`);
                    statusCell.innerHTML = `<span class="badge bg-success">${data.status_label}</span>`;

                    const confirmBtn = document.querySelector(`.confirm-order-btn[data-id="${confirmOrderPk}"]`);
                    confirmBtn?.remove();

                    bootstrap.Modal.getInstance(confirmModal).hide();
                } else {
                    alert("Erro: " + (data.error || "Não foi possível confirmar o pedido."));
                    btn.disabled = false;
                    btn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Confirmar';
                }
            })
            .catch(() => {
                alert("Erro inesperado. Tente novamente.");
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Confirmar';
            });
        });
    }
});