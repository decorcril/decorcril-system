document.addEventListener("DOMContentLoaded", function () {
    const modalEl = document.getElementById("viewOrderModal");
    if (!modalEl) return;

    const fmt = v => parseFloat(v || 0).toLocaleString("pt-BR", { minimumFractionDigits: 2 });
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };

    const FREE_SALE_TYPES = ["exchange", "maintenance", "advertising"];
    const FREE_SALE_LABELS = {
        exchange:    "Troca",
        maintenance: "Manutenção",
        advertising: "Publicidade",
    };

    // ================= ABRIR MODAL =================
    document.addEventListener("click", function (e) {
        const btn = e.target.closest(".open-view-order-btn");
        if (!btn) return;
        loadOrder(btn.dataset.id);
        new bootstrap.Modal(modalEl).show();
    });

    // ================= CARREGAR DADOS =================
    const loadOrder = pk => {
        set("view-order-number", "...");
        document.getElementById("view-status-badge").innerHTML = "";
        document.getElementById("view-free-sale-alert").classList.add("d-none");
        document.getElementById("view-items-body").innerHTML =
            `<tr><td colspan="6" class="text-center text-muted py-3">Carregando...</td></tr>`;
        document.getElementById("view-payments-list").innerHTML =
            `<p class="text-muted text-center small py-2">Carregando...</p>`;

        fetch(`/vendas/orders/${pk}/detail/`)
            .then(r => r.json())
            .then(renderOrder)
            .catch(() => {
                document.getElementById("view-items-body").innerHTML =
                    `<tr><td colspan="6" class="text-center text-danger">Erro ao carregar pedido.</td></tr>`;
            });
    };

    const renderOrder = data => {
        // Cabeçalho
        set("view-order-number", data.number);
        document.getElementById("view-status-badge").innerHTML =
            `<span class="badge ${data.status_color} fs-6">${data.status_label}</span>`;
        set("view-created-at", data.created_at);
        set("view-created-by", data.created_by);

        // Alerta de venda sem cobrança
        const alertEl = document.getElementById("view-free-sale-alert");
        if (FREE_SALE_TYPES.includes(data.sale_type_raw)) {
            const label = FREE_SALE_LABELS[data.sale_type_raw] || data.sale_type;
            document.getElementById("view-free-sale-type").textContent = label;
            alertEl.classList.remove("d-none");
        } else {
            alertEl.classList.add("d-none");
        }

        // Cliente
        set("view-client-name",     data.client.name);
        set("view-client-document", data.client.document);
        set("view-client-type",     data.client.type);
        set("view-client-phone",    data.client.phone);
        set("view-client-email",    data.client.email);
        set("view-client-address",  data.client.address);

        // Comercial
        set("view-sale-type",        data.sale_type);
        set("view-contact",          data.contact);
        set("view-customer-order",   data.customer_order);
        set("view-payment-terms",    data.payment_terms);
        set("view-carrier",          data.carrier);
        set("view-freight",          `R$ ${fmt(data.freight)}`);
        set("view-down-payment-pct", `${fmt(data.down_payment_percent)}%`);
        set("view-down-payment-val", `R$ ${fmt(data.down_payment_value)}`);

        // Totais
        set("view-total-freight", `R$ ${fmt(data.freight)}`);
        set("view-total-amount",  `R$ ${fmt(data.total_amount)}`);
        set("view-total-paid",    `R$ ${fmt(data.total_paid)}`);
        set("view-remaining",     `R$ ${fmt(data.remaining)}`);

        // Observações
        set("view-notes",          data.notes);
        set("view-internal-notes", data.internal_notes);

        // Itens
        const tbody = document.getElementById("view-items-body");
        if (!data.items.length) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-3">Nenhum item.</td></tr>`;
        } else {
            tbody.innerHTML = data.items.map(item => {
                const specs = [];
                if (item.thickness)  specs.push(`<div><strong>Espessura:</strong> ${item.thickness}</div>`);
                if (item.color)      specs.push(`<div><strong>Cor:</strong> ${item.color}</div>`);
                if (item.color_obs)  specs.push(`<div><strong>Obs. cor:</strong> ${item.color_obs}</div>`);
                if (item.dimensions) specs.push(`<div><strong>Dimensões:</strong> ${item.dimensions}</div>`);
                if (item.voltage)    specs.push(`<div><strong>Tensão:</strong> ${item.voltage}</div>`);
                if (item.led)        specs.push(`<div><strong>LED:</strong> ${item.led}</div>`);

                return `
                <tr>
                    <td>
                        <div class="fw-semibold">${item.name}</div>
                        ${item.sku ? `<small class="text-muted font-monospace">${item.sku}</small>` : ""}
                    </td>
                    <td class="small">${specs.length ? specs.join("") : "<span class='text-muted'>—</span>"}</td>
                    <td class="text-center">${item.quantity}</td>
                    <td class="text-end">R$ ${fmt(item.unit_price)}</td>
                    <td class="text-center">${fmt(item.discount)}%</td>
                    <td class="text-end fw-semibold">R$ ${fmt(item.subtotal)}</td>
                </tr>`;
            }).join("");
        }

        // Pagamentos
        const payList = document.getElementById("view-payments-list");
        if (!data.payments.length) {
            payList.innerHTML = `<p class="text-muted text-center small py-2">Nenhum pagamento registrado.</p>`;
        } else {
            payList.innerHTML = data.payments.map(p => `
                <div class="d-flex justify-content-between align-items-start border rounded p-2 mb-2 small">
                    <div>
                        <span class="badge bg-primary me-1">${p.method_label}</span>
                        <strong>R$ ${fmt(p.amount)}</strong>
                        ${p.transaction ? `<span class="fw-semibold ms-2 font-monospace">Nº Transação: ${p.transaction}</span>` : ""}
                        <div class="text-muted mt-1">${p.paid_at} · ${p.created_by}</div>
                    </div>
                </div>
            `).join("");
        }
    };
});