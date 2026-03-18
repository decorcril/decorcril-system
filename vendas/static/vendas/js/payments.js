document.addEventListener("DOMContentLoaded", function () {
    const modalEl = document.getElementById("paymentsModal");
    if (!modalEl) return;

    let currentOrderPk = null;

    const fmt       = v => parseFloat(v || 0).toLocaleString("pt-BR", { minimumFractionDigits: 2 });
    const csrfToken = () => document.cookie.match(/csrftoken=([^;]+)/)?.[1] ?? "";

    // ================= ABRIR MODAL =================
    document.addEventListener("click", function (e) {
        const btn = e.target.closest(".open-payments-btn");
        if (!btn) return;

        currentOrderPk = btn.dataset.id;
        document.getElementById("pay-order-number").textContent = btn.dataset.number;
        resetForm();
        loadPayments();

        new bootstrap.Modal(modalEl).show();
    });

    // ================= ATUALIZA ROW DA TABELA =================
    const updateRowStatus = (newStatus, statusLabel) => {
        if (!newStatus || !statusLabel) return;

        const statusCell = document.getElementById(`order-status-${currentOrderPk}`);
        if (statusCell) {
            const colorMap = {
                open:          "bg-primary",
                in_production: "bg-success",
                picking:       "bg-info text-dark",
                invoiced:      "bg-secondary",
                shipped:       "bg-dark",
                delivered:     "bg-success",
                canceled:      "bg-danger",
            };
            const color = colorMap[newStatus] || "bg-light text-dark";
            statusCell.innerHTML = `<span class="badge ${color}">${statusLabel}</span>`;
        }

        const deleteBtn = document.querySelector(`#order-row-${currentOrderPk} .btn-outline-danger, #order-row-${currentOrderPk} .btn-outline-secondary:last-child`);
        if (deleteBtn) {
            const deletable = ["open", "canceled"].includes(newStatus);
            deleteBtn.disabled  = !deletable;
            deleteBtn.className = `btn btn-sm ${deletable ? "btn-outline-danger" : "btn-outline-secondary"}`;
            deleteBtn.title     = deletable ? "Excluir pedido" : `Exclusão bloqueada — pedido em ${statusLabel}`;
        }
    };

    // ================= CARREGAR PAGAMENTOS =================
    const loadPayments = () => {
        const list = document.getElementById("pay-list");
        list.innerHTML = `<p class="text-muted text-center small py-2">Carregando...</p>`;

        fetch(`/vendas/orders/${currentOrderPk}/payments/`)
            .then(r => r.json())
            .then(data => {
                updateTotals(data);
                renderPayments(data.payments);
            })
            .catch(() => {
                list.innerHTML = `<p class="text-danger text-center small">Erro ao carregar pagamentos.</p>`;
            });
    };

    const updateTotals = data => {
        document.getElementById("pay-total-amount").textContent = fmt(data.total_amount);
        document.getElementById("pay-down-payment").textContent = fmt(data.down_payment_value);
        document.getElementById("pay-total-paid").textContent   = fmt(data.total_paid);
        document.getElementById("pay-remaining").textContent    = fmt(data.remaining);

        const termsWrap = document.getElementById("pay-payment-terms-wrap");
        const termsEl   = document.getElementById("pay-payment-terms");
        if (data.payment_terms) {
            termsEl.textContent = data.payment_terms;
            termsWrap.classList.remove("d-none");
        } else {
            termsWrap.classList.add("d-none");
        }
    };

    const renderPayments = payments => {
        const list = document.getElementById("pay-list");
        if (!payments.length) {
            list.innerHTML = `<p class="text-muted text-center small py-2">Nenhum pagamento registrado.</p>`;
            return;
        }

        list.innerHTML = payments.map(p => `
            <div class="border rounded p-2 mb-2 small">
                <div class="row align-items-center">
                    <div class="col-md-3">
                        <span class="badge bg-primary mb-1">${p.method_label}</span>
                        <div class="fw-semibold">R$ ${fmt(p.amount)}</div>
                    </div>
                    <div class="col-md-7">
                        ${p.transaction ? `<div class="text-muted font-monospace">Transação: ${p.transaction}</div>` : ""}
                        <div class="text-muted">${p.paid_at} • Registrado por: ${p.created_by}</div>
                        ${p.notes ? `<div class="text-muted fst-italic">${p.notes}</div>` : ""}
                    </div>
                    <div class="col-md-2 text-end">
                        <button type="button"
                            class="btn btn-sm btn-outline-danger delete-payment-btn"
                            data-payment-id="${p.id}"
                            title="Remover pagamento">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `).join("");
    };

    // ================= DELETAR PAGAMENTO =================
    document.addEventListener("click", function (e) {
        const btn = e.target.closest(".delete-payment-btn");
        if (!btn) return;

        if (!confirm("Remover este pagamento?")) return;

        fetch(`/vendas/payments/${btn.dataset.paymentId}/delete/`, {
            method:  "POST",
            headers: { "X-CSRFToken": csrfToken() },
        })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    loadPayments();
                    updateRowStatus(data.new_status, data.status_label);
                } else {
                    alert(data.error || "Erro ao remover pagamento.");
                }
            })
            .catch(() => alert("Erro inesperado."));
    });

    // ================= MÁSCARA DE VALOR =================
    const amountInput = document.getElementById("pay-amount");
    if (amountInput) {
        amountInput.addEventListener("input", function () {
            let raw = this.value.replace(/\D/g, "");
            if (!raw) { this.value = ""; return; }
            const num = parseInt(raw) / 100;
            this.value = num.toLocaleString("pt-BR", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            });
        });
    }

    // ================= HINTS DE TRANSAÇÃO =================
    const methodSelect = document.getElementById("pay-method");
    if (methodSelect) {
        methodSelect.addEventListener("change", function () {
            const hints = {
                pix:      "Código da transação PIX *",
                debit:    "NSU do cartão *",
                credit:   "NSU do cartão *",
                boleto:   "Número do boleto *",
                transfer: "Número da transferência *",
                cash:     "",
            };
            const hint       = document.getElementById("pay-transaction-hint");
            const transWrap  = document.getElementById("pay-transaction-wrap");
            const transInput = document.getElementById("pay-transaction");

            hint.textContent = hints[this.value] || "";

            if (this.value === "cash") {
                transWrap.classList.add("d-none");
                transInput.value = "";
            } else {
                transWrap.classList.remove("d-none");
            }
        });
    }

    // ================= SUBMIT =================
    const submitBtn = document.getElementById("pay-submit-btn");
    if (submitBtn) {
        submitBtn.addEventListener("click", function () {
            const method     = document.getElementById("pay-method").value;
            const amountRaw  = document.getElementById("pay-amount").value
                .replace(/\./g, "")
                .replace(",", ".");
            const transaction = document.getElementById("pay-transaction").value.trim();
            const notes       = document.getElementById("pay-notes").value.trim();

            document.getElementById("pay-transaction").classList.remove("is-invalid");

            if (!method)                          return alert("Selecione a forma de pagamento.");
            if (!amountRaw || parseFloat(amountRaw) <= 0) return alert("Informe um valor válido.");
            if (method !== "cash" && !transaction) return alert("Informe o número de transação.");

            const btn = this;
            btn.disabled  = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Salvando...';

            const body = new FormData();
            body.append("method",      method);
            body.append("amount",      amountRaw);
            body.append("transaction", transaction);
            body.append("notes",       notes);

            fetch(`/vendas/orders/${currentOrderPk}/payments/add/`, {
                method:  "POST",
                headers: { "X-CSRFToken": csrfToken() },
                body,
            })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        resetForm();
                        loadPayments();
                        updateRowStatus(data.new_status, data.status_label);
                    } else {
                        if (data.errors?.transaction) {
                            const input = document.getElementById("pay-transaction");
                            const error = document.getElementById("pay-transaction-error");
                            input.classList.add("is-invalid");
                            error.textContent = data.errors.transaction[0];
                        } else {
                            alert(Object.values(data.errors || {}).flat().join("\n") || data.error || "Erro desconhecido.");
                        }
                    }
                })
                .catch(() => alert("Erro inesperado."))
                .finally(() => {
                    btn.disabled  = false;
                    btn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Registrar Pagamento';
                });
        });
    }

    // ================= RESET =================
    const resetForm = () => {
        if (document.getElementById("pay-method"))      document.getElementById("pay-method").value      = "";
        if (document.getElementById("pay-amount"))      document.getElementById("pay-amount").value      = "";
        if (document.getElementById("pay-transaction")) document.getElementById("pay-transaction").value = "";
        if (document.getElementById("pay-notes"))       document.getElementById("pay-notes").value       = "";
        const transInput = document.getElementById("pay-transaction");
        if (transInput) transInput.classList.remove("is-invalid");
        const hint = document.getElementById("pay-transaction-hint");
        if (hint) hint.textContent = "(opcional)";
    };

    modalEl.addEventListener("hidden.bs.modal", resetForm);
});