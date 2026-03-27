document.addEventListener("DOMContentLoaded", function () {
    const modalEl = document.getElementById("confirmOrderModal");
    let currentOrderPk = null;

    // Abre o modal ao clicar no botão de confirmar
    document.addEventListener("click", function (e) {
        const btn = e.target.closest(".confirm-order-btn");
        if (!btn) return;

        currentOrderPk = btn.dataset.id;
        document.getElementById("confirm-order-number").textContent    = btn.dataset.number;
        document.getElementById("confirm-order-client").textContent     = btn.dataset.client;
        document.getElementById("confirm-order-downpayment").textContent = `R$ ${parseFloat(btn.dataset.downpayment || 0).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`;

        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    });

    // Submit do form de confirmação
    const form = document.getElementById("confirmOrderForm");
    form.addEventListener("submit", function (e) {
        e.preventDefault();
        if (!currentOrderPk) return;

        const btn = form.querySelector("button[type=submit]");
        btn.disabled  = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Confirmando...';

        fetch(`/vendas/orders/${currentOrderPk}/confirm/`, {
            method: "POST",
            headers: {
                "X-CSRFToken": document.cookie.match(/csrftoken=([^;]+)/)?.[1] ?? "",
            },
        })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    const statusCell = document.getElementById(`order-status-${currentOrderPk}`);
                    if (statusCell) {
                        statusCell.innerHTML = `<span class="badge bg-success">${data.status_label}</span>`;
                    }

                    const confirmBtn = document.querySelector(`.confirm-order-btn[data-id="${currentOrderPk}"]`);
                    confirmBtn?.remove();

                    bootstrap.Modal.getInstance(modalEl).hide();
                } else {
                    alert("Erro: " + (data.error || "Não foi possível confirmar o pedido."));
                    btn.disabled  = false;
                    btn.innerHTML = "Confirmar pagamento";
                }
            })
            .catch(() => {
                alert("Erro inesperado. Tente novamente.");
                btn.disabled  = false;
                btn.innerHTML = "Confirmar pagamento";
            });
    });

    // Reseta o botão e estado ao fechar o modal
    modalEl.addEventListener("hidden.bs.modal", function () {
        const btn = form.querySelector("button[type=submit]");
        btn.disabled  = false;
        btn.innerHTML = "Confirmar pagamento";
        currentOrderPk = null;
    });
});