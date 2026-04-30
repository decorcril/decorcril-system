document.addEventListener("DOMContentLoaded", function () {
    const modalEl = document.getElementById("viewOrderModal");
    if (!modalEl) return;

    const fmt     = v => parseFloat(v || 0).toLocaleString("pt-BR", { minimumFractionDigits: 2 });
    const setText = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    };

    const FREE_SALE_TYPES  = ["exchange", "maintenance", "advertising", "replacement"];
    const FREE_SALE_LABELS = {
        exchange:    "Troca",
        maintenance: "Manutenção",
        advertising: "Publicidade",
        replacement: "Reposição",
    };

    // ── Abrir modal ───────────────────────────────────────────
    document.addEventListener("click", function (e) {
        const btn = e.target.closest(".open-view-order-btn");
        if (!btn) return;
        loadOrder(btn.dataset.id);
        new bootstrap.Modal(modalEl).show();
    });

    // ── Carregar dados ────────────────────────────────────────
    const loadOrder = pk => {
        setText("view-order-number", "...");
        document.getElementById("view-status-badge").innerHTML = "";
        document.getElementById("view-free-sale-alert").classList.add("d-none");
        document.getElementById("view-items-body").innerHTML =
            `<tr><td colspan="5" class="text-center text-muted py-3">Carregando...</td></tr>`;
        document.getElementById("view-payments-list").innerHTML =
            `<p class="text-muted text-center small py-2">Carregando...</p>`;

        fetch(`/vendas/orders/${pk}/detail/`)
            .then(r => r.json())
            .then(renderOrder)
            .catch(() => {
                document.getElementById("view-items-body").innerHTML =
                    `<tr><td colspan="5" class="text-center text-danger">Erro ao carregar pedido.</td></tr>`;
            });
    };

    // ── Renderizar pedido ─────────────────────────────────────
    const renderOrder = data => {

        // Cabeçalho
        setText("view-order-number", data.number);
        document.getElementById("view-status-badge").innerHTML =
            `<span class="badge ${data.status_color} fs-6">${data.status_label}</span>`;
        setText("view-created-at", data.created_at);
        setText("view-created-by", data.created_by);

        // Alerta venda gratuita
        const alertEl = document.getElementById("view-free-sale-alert");
        if (FREE_SALE_TYPES.includes(data.sale_type_raw)) {
            setText("view-free-sale-type", FREE_SALE_LABELS[data.sale_type_raw] || data.sale_type);
            alertEl.classList.remove("d-none");
        } else {
            alertEl.classList.add("d-none");
        }

        // Cliente
        setText("view-client-name",      data.client.name      || "—");
        setText("view-client-document",  data.client.document  || "—");
        setText("view-client-type",      data.client.type      || "—");
        setText("view-client-phone",     data.client.phone     || "—");
        setText("view-client-whatsapp",  data.client.whatsapp  || "—");
        setText("view-client-email",     data.client.email     || "—");
        setText("view-client-address",   data.client.address   || "—");

        // Comercial
        setText("view-sale-type",        data.sale_type      || "—");
        setText("view-contact",          data.contact        || "—");
        setText("view-customer-order",   data.customer_order || "—");
        setText("view-payment-terms",    data.payment_terms  || "—");
        setText("view-carrier",          data.carrier        || "—");
        setText("view-freight",          `R$ ${fmt(data.freight)}`);
        setText("view-down-payment-pct", data.down_payment_percent ? `${fmt(data.down_payment_percent)}%` : "—");
        setText("view-down-payment-val", `R$ ${fmt(data.down_payment_value)}`);

        // Totais
        setText("view-total-products", `R$ ${fmt(data.total_products)}`);
        setText("view-total-discount", `R$ ${fmt(data.total_discount)}`);
        setText("view-total-freight",  `R$ ${fmt(data.freight)}`);
        setText("view-total-amount",   `R$ ${fmt(data.total_amount)}`);
        setText("view-total-paid",     `R$ ${fmt(data.total_paid)}`);
        setText("view-remaining",      `R$ ${fmt(data.remaining)}`);

        // Observações
        setText("view-notes",          data.notes          || "—");
        setText("view-internal-notes", data.internal_notes || "—");

        // ── Itens ─────────────────────────────────────────────
        const tbody = document.getElementById("view-items-body");
        if (!data.items || !data.items.length) {
            tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-3">Nenhum item neste pedido.</td></tr>`;
        } else {
            tbody.innerHTML = data.items.map(item => `
                <tr>
                    <td class="text-center">${item.quantity || 0}</td>
                    <td class="text-center">${item.sku || ""}</td>
                    <td>${item.name || ""}</td>
                    <td class="text-end">R$ ${fmt(item.unit_price)}</td>
                    <td class="text-end fw-semibold">R$ ${fmt(item.subtotal)}</td>
                </tr>
            `).join("");
        }

        // ── Pagamentos ────────────────────────────────────────
        const payList = document.getElementById("view-payments-list");
        if (!data.payments || !data.payments.length) {
            payList.innerHTML = `<p class="text-muted text-center small py-2">Nenhum pagamento registrado.</p>`;
        } else {
            payList.innerHTML = data.payments.map(p => `
                <div class="d-flex justify-content-between align-items-center border rounded p-2 mb-2 small">
                    <div>
                        <span class="badge bg-primary me-1">${p.method_label}</span>
                        <span class="fw-semibold">R$ ${fmt(p.amount)}</span>
                        ${p.transaction ? `<span class="text-muted ms-2">Nº ${p.transaction}</span>` : ""}
                        <span class="text-muted ms-2">${p.paid_at || ""}</span>
                    </div>
                    <div class="text-muted">${p.created_by || ""}</div>
                </div>
            `).join("");
        }
    };
});