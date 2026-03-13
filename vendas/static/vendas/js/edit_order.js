document.addEventListener("DOMContentLoaded", function () {
    const modalEl = document.getElementById("editOrderModal");
    if (!modalEl) return;

    const modal   = new bootstrap.Modal(modalEl);
    const fmt     = v => parseFloat(v || 0).toLocaleString("pt-BR", { minimumFractionDigits: 2 });
    const getCsrf = () => document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";

    // Status que bloqueiam edição
    const LOCKED_STATUSES = ["picking", "invoiced", "shipped", "delivered", "canceled"];

    let currentOrderId   = null;
    let selectedProduct  = null;  // produto escolhido no autocomplete

    // ── Elementos fixos ──────────────────────────────────────
    const itemsBody      = document.getElementById("edit-items-body");
    const totalEl        = document.getElementById("edit-total");
    const productInput   = document.getElementById("edit-product-input");
    const productResults = document.getElementById("edit-product-results");

    // ================= ABRIR MODAL =================
    document.addEventListener("click", function (e) {
        const btn = e.target.closest(".open-edit-order-btn");
        if (!btn) return;
        currentOrderId  = btn.dataset.id;
        selectedProduct = null;
        loadOrder(currentOrderId);
        modal.show();
    });

    // ================= CARREGAR PEDIDO =================
    const loadOrder = pk => {
        document.getElementById("edit-order-number").textContent = "...";
        document.getElementById("edit-locked-alert").classList.add("d-none");
        document.getElementById("edit-form-body").classList.remove("d-none");
        itemsBody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-3">Carregando...</td></tr>`;

        fetch(`/vendas/orders/${pk}/detail/`)
            .then(r => r.json())
            .then(data => {
                document.getElementById("edit-order-number").textContent = data.number;

                // Verifica se pode editar
                if (LOCKED_STATUSES.includes(data.status)) {
                    document.getElementById("edit-locked-alert").classList.remove("d-none");
                    document.getElementById("edit-form-body").classList.add("d-none");
                    document.getElementById("edit-save-btn").disabled = true;
                    return;
                }
                document.getElementById("edit-save-btn").disabled = false;

                // Preenche campos comerciais
                setSelect("edit-sale-type",   data.sale_type_raw);
                setVal("edit-contact",         data.contact === "—"          ? "" : data.contact);
                setVal("edit-customer-order",  data.customer_order === "—"   ? "" : data.customer_order);
                setVal("edit-payment-terms",   data.payment_terms === "—"    ? "" : data.payment_terms);
                setSelect("edit-carrier",      data.carrier === "—"          ? "" : data.carrier);
                setVal("edit-freight",         data.freight);
                setVal("edit-down-payment",    data.down_payment_percent);

                // Observações
                setVal("edit-notes",          data.notes === "—"          ? "" : data.notes);
                setVal("edit-internal-notes", data.internal_notes === "—" ? "" : data.internal_notes);

                // Itens
                renderItems(data.items);
            })
            .catch(() => {
                itemsBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">Erro ao carregar pedido.</td></tr>`;
            });
    };

    const setVal    = (id, v) => { const el = document.getElementById(id); if (el) el.value = v ?? ""; };
    const setSelect = (id, v) => {
        const el = document.getElementById(id);
        if (!el) return;
        const opt = [...el.options].find(o => o.value === v);
        el.value = opt ? v : "";
    };

    // ================= RENDERIZAR ITENS =================
    const renderItems = items => {
        if (!items.length) {
            itemsBody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-3">Nenhum item.</td></tr>`;
            recalcTotal();
            return;
        }
        itemsBody.innerHTML = items.map(item => buildItemRow(item)).join("");
        recalcTotal();
    };

    const buildItemRow = item => {
        const discountPct = parseFloat(item.discount || 0);
        const unitPrice   = parseFloat(item.unit_price || 0);
        const qty         = parseInt(item.quantity || 1);
        const subtotal    = unitPrice * qty * (1 - discountPct / 100);
        return `
        <tr data-item-id="${item.id}" data-unit-price="${unitPrice}">
            <td>
                <div class="fw-semibold">${item.name}</div>
                ${item.sku ? `<small class="text-muted font-monospace">${item.sku}</small>` : ""}
            </td>
            <td class="text-end">R$ ${fmt(unitPrice)}</td>
            <td class="text-center">
                <input type="number" min="1" value="${qty}"
                    class="form-control form-control-sm text-center item-qty"
                    style="width:70px; margin:auto;">
            </td>
            <td class="text-center">
                <input type="number" min="0" max="100" step="0.01" value="${fmt(discountPct).replace(',', '.')}"
                    class="form-control form-control-sm text-center item-disc"
                    style="width:80px; margin:auto;">
            </td>
            <td class="text-end fw-semibold item-subtotal">R$ ${fmt(subtotal)}</td>
            <td class="text-center">
                <button type="button" class="btn btn-sm btn-outline-danger btn-remove-item" title="Remover item">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        </tr>`;
    };

    // ================= RECALC TOTAL =================
    const recalcTotal = () => {
        let total = 0;
        itemsBody.querySelectorAll("tr[data-item-id]").forEach(row => {
            const price = parseFloat(row.dataset.unitPrice || 0);
            const qty   = parseInt(row.querySelector(".item-qty")?.value || 1);
            const disc  = parseFloat(row.querySelector(".item-disc")?.value || 0);
            const sub   = price * qty * (1 - disc / 100);
            row.querySelector(".item-subtotal").textContent = `R$ ${fmt(sub)}`;
            total += sub;
        });
        const freight = parseFloat(document.getElementById("edit-freight")?.value || 0);
        totalEl.textContent = fmt(total + freight);
    };

    // Recalcula ao digitar qty/desconto/frete
    itemsBody.addEventListener("input", e => {
        if (e.target.matches(".item-qty, .item-disc")) recalcTotal();
    });
    document.getElementById("edit-freight")?.addEventListener("input", recalcTotal);

    // ================= REMOVER ITEM =================
    itemsBody.addEventListener("click", async function (e) {
        const btn = e.target.closest(".btn-remove-item");
        if (!btn) return;
        const row    = btn.closest("tr");
        const itemId = row.dataset.itemId;

        if (!confirm("Remover este item do pedido?")) return;

        const res = await fetch(`/vendas/orders/items/${itemId}/delete/`, {
            method: "POST",
            headers: { "X-CSRFToken": getCsrf() },
        });
        const data = await res.json();
        if (data.success) {
            row.remove();
            recalcTotal();
            if (!itemsBody.querySelector("tr[data-item-id]")) {
                itemsBody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-3">Nenhum item.</td></tr>`;
            }
        } else {
            alert("Erro ao remover item: " + (data.error || ""));
        }
    });

    // ================= AUTOCOMPLETE PRODUTO =================
    const searchProducts = query => {
        const url = productInput.dataset.url;
        if (!url || query.length < 2) { productResults.classList.add("d-none"); return; }
        fetch(`${url}?q=${encodeURIComponent(query)}`)
            .then(r => r.json())
            .then(data => {
                if (!data.results?.length) { productResults.classList.add("d-none"); return; }
                productResults.innerHTML = data.results.map(p =>
                    `<button type="button" class="list-group-item list-group-item-action"
                        data-id="${p.id}" data-name="${p.name}" data-sku="${p.sku || ''}"
                        data-price="${p.price}">
                        <span class="fw-semibold">${p.name}</span>
                        ${p.sku ? `<small class="text-muted ms-2 font-monospace">${p.sku}</small>` : ""}
                        <span class="float-end text-success small">R$ ${fmt(p.price)}</span>
                    </button>`
                ).join("");
                productResults.classList.remove("d-none");
            });
    };

    productInput?.addEventListener("input", e => searchProducts(e.target.value));
    document.getElementById("edit-btn-search-product")?.addEventListener("click", () => searchProducts(productInput.value));

    productResults?.addEventListener("click", e => {
        const btn = e.target.closest(".list-group-item");
        if (!btn) return;
        selectedProduct = { id: btn.dataset.id, name: btn.dataset.name, sku: btn.dataset.sku, price: btn.dataset.price };
        productInput.value = btn.dataset.name;
        productResults.classList.add("d-none");
    });

    document.addEventListener("click", e => {
        if (!productResults?.contains(e.target) && e.target !== productInput) {
            productResults?.classList.add("d-none");
        }
    });

    // ================= ADICIONAR ITEM =================
    document.getElementById("edit-btn-add-product")?.addEventListener("click", async () => {
        if (!selectedProduct) { alert("Selecione um produto primeiro."); return; }

        const res = await fetch(`/vendas/orders/${currentOrderId}/items/add/`, {
            method: "POST",
            headers: { "X-CSRFToken": getCsrf(), "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({
                product_id: selectedProduct.id,
                unit_price: selectedProduct.price,
                quantity:   1,
                discount:   0,
            }),
        });
        const data = await res.json();
        if (data.success) {
            // Recarrega itens do servidor para ter o id correto
            fetch(`/vendas/orders/${currentOrderId}/detail/`)
                .then(r => r.json())
                .then(d => renderItems(d.items));
            productInput.value = "";
            selectedProduct    = null;
        } else {
            alert("Erro ao adicionar item: " + (data.error || ""));
        }
    });

    // ================= SALVAR PEDIDO =================
    document.getElementById("edit-save-btn")?.addEventListener("click", async () => {
        // 1. Salva cada item modificado
        const itemRows = itemsBody.querySelectorAll("tr[data-item-id]");
        for (const row of itemRows) {
            const itemId = row.dataset.itemId;
            const price  = parseFloat(row.dataset.unitPrice);
            const qty    = row.querySelector(".item-qty").value;
            const disc   = row.querySelector(".item-disc").value;

            await fetch(`/vendas/orders/items/${itemId}/edit/`, {
                method: "POST",
                headers: { "X-CSRFToken": getCsrf(), "Content-Type": "application/x-www-form-urlencoded" },
                body: new URLSearchParams({ unit_price: price, quantity: qty, discount: disc }),
            });
        }

        // 2. Salva campos do pedido
        const body = new URLSearchParams({
            sale_type:           document.getElementById("edit-sale-type").value,
            contact:             document.getElementById("edit-contact").value,
            customer_order:      document.getElementById("edit-customer-order").value,
            payment_terms:       document.getElementById("edit-payment-terms").value,
            carrier:             document.getElementById("edit-carrier").value,
            freight:             document.getElementById("edit-freight").value,
            down_payment_percent:document.getElementById("edit-down-payment").value,
            notes:               document.getElementById("edit-notes").value,
            internal_notes:      document.getElementById("edit-internal-notes").value,
        });

        const res = await fetch(`/vendas/orders/${currentOrderId}/update/`, {
            method: "POST",
            headers: { "X-CSRFToken": getCsrf(), "Content-Type": "application/x-www-form-urlencoded" },
            body,
        });
        const data = await res.json();
        if (data.success) {
            modal.hide();
            location.reload();
        } else {
            alert("Erro ao salvar pedido: " + (data.error || ""));
        }
    });
});