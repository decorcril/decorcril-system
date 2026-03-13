(function () {
    "use strict";

    function initOrderModal() {
        const modal = document.getElementById("createOrderModal");
        if (!modal || modal._orderInitialized) return;
        modal._orderInitialized = true;

        const CLIENT_URL  = document.getElementById("client_input").dataset.url;
        const PRODUCT_URL = document.getElementById("order_product_input").dataset.url;
        const CREATE_URL  = document.getElementById("orderForm").dataset.url;

        let items = [];
        let selectedProduct = null;

        // ── Utilitários ───────────────────────────────────────
        const $ = id => document.getElementById(id);

        const fmt = v =>
            parseFloat(v || 0).toLocaleString("pt-BR", { minimumFractionDigits: 2 });

        const parseBrl = v =>
            parseFloat((v || "0").replace(/\./g, "").replace(",", ".")) || 0;

        const fmtDoc = detail => {
            const parts = (detail || "").split(" · ");
            if (parts.length < 2) return detail || "";
            const code = parts[0];
            const doc  = parts[1].replace(/\D/g, "");
            let fmtd;
            if (doc.length === 11)
                fmtd = doc.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4");
            else if (doc.length === 14)
                fmtd = doc.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, "$1.$2.$3/$4-$5");
            else
                fmtd = doc;
            return `${code} · ${fmtd}`;
        };

        const fmtPhone = v => {
            if (!v) return "";
            const d = v.replace(/\D/g, "");
            if (d.length === 11) return d.replace(/(\d{2})(\d{5})(\d{4})/, "($1) $2-$3");
            if (d.length === 10) return d.replace(/(\d{2})(\d{4})(\d{4})/, "($1) $2-$3");
            return v;
        };

        const applyBrlMask = input => {
            input.addEventListener("input", function () {
                const digits = this.value.replace(/\D/g, "");
                if (!digits) { this.value = "0,00"; return; }
                this.value = (parseInt(digits, 10) / 100).toLocaleString("pt-BR", {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                });
            });
        };

        applyBrlMask($("order_freight_field"));

        // ── Reset ─────────────────────────────────────────────
        const reset = () => {
            items           = [];
            selectedProduct = null;
            $("client_input").value             = "";
            $("client_id").value                = "";
            $("order_product_input").value      = "";
            $("order_down_payment_field").value = "0";
            $("order_freight_field").value      = "0,00";
            $("client_results").classList.add("d-none");
            $("order_product_results").classList.add("d-none");
            $("client_info_card").classList.add("d-none");
            renderTable();
        };

        // ── Cliente ───────────────────────────────────────────
        const showClient = c => {
            $("client_info_name").textContent     = c.text;
            $("client_info_document").textContent = fmtDoc(c.detail);
            $("client_info_badge").textContent    = c.badge || "";

            [
                ["client_info_phone",   "client_info_phone_wrap",   fmtPhone(c.phone)],
                ["client_info_email",   "client_info_email_wrap",   c.email],
                ["client_info_address", "client_info_address_wrap", c.address],
            ].forEach(([elId, wrapId, val]) => {
                $(elId).textContent = val || "";
                $(wrapId).classList.toggle("d-none", !val);
            });

            $("client_info_card").classList.remove("d-none");
        };

        const renderClientResults = data => {
            const box = $("client_results");
            box.innerHTML = "";
            if (!data.length) { box.classList.add("d-none"); return; }

            data.forEach(c => {
                const a = document.createElement("a");
                a.href      = "#";
                a.className = "list-group-item list-group-item-action";
                a.innerHTML = `<div class="fw-semibold">${c.text}</div>
                               <small class="text-muted">${fmtDoc(c.detail) || ""}</small>`;
                a.onclick = e => {
                    e.preventDefault();
                    $("client_input").value = c.text;
                    $("client_id").value    = c.id;
                    box.classList.add("d-none");
                    showClient(c);
                };
                box.appendChild(a);
            });
            box.classList.remove("d-none");
        };

        const searchClient = () => {
            const q = $("client_input").value.trim();
            if (q.length < 2) return;
            fetch(`${CLIENT_URL}?q=${encodeURIComponent(q)}`)
                .then(r => r.json())
                .then(renderClientResults)
                .catch(console.error);
        };

        $("btn_search_client").addEventListener("click", searchClient);
        $("client_input").addEventListener("keyup", function () {
            this.value.trim().length >= 2
                ? searchClient()
                : $("client_results").classList.add("d-none");
        });
        $("btn_clear_client").addEventListener("click", () => {
            $("client_input").value = "";
            $("client_id").value    = "";
            $("client_results").classList.add("d-none");
            $("client_info_card").classList.add("d-none");
        });

        // ── Produto ───────────────────────────────────────────
        const renderProductResults = data => {
            const box = $("order_product_results");
            box.innerHTML = "";
            if (!data.length) { box.classList.add("d-none"); return; }

            data.forEach(p => {
                const a = document.createElement("a");
                a.href      = "#";
                a.className = "list-group-item list-group-item-action";
                a.innerHTML = `${p.text}
                               <small class="text-muted ms-2">${p.sku} · R$ ${fmt(p.price)}</small>`;
                a.onclick = e => {
                    e.preventDefault();
                    selectedProduct = p;
                    $("order_product_input").value = p.text;
                    box.classList.add("d-none");
                };
                box.appendChild(a);
            });
            box.classList.remove("d-none");
        };

        const searchProduct = () => {
            const q = $("order_product_input").value.trim();
            if (q.length < 2) return;
            fetch(`${PRODUCT_URL}?q=${encodeURIComponent(q)}`)
                .then(r => r.json())
                .then(renderProductResults)
                .catch(console.error);
        };

        $("btn_search_product").addEventListener("click", searchProduct);
        $("order_product_input").addEventListener("keyup", function () {
            this.value.trim().length >= 2
                ? searchProduct()
                : $("order_product_results").classList.add("d-none");
        });

        $("btn_add_product").addEventListener("click", () => {
            if (!selectedProduct) return;

            if (items.find(i => i.product_id === selectedProduct.product_id)) {
                selectedProduct = null;
                $("order_product_input").value = "";
                return;
            }

            items.push({
                product_id: selectedProduct.product_id,
                name:       selectedProduct.text,
                unit_price: parseFloat(selectedProduct.price) || 0,
                quantity:   1,
                discount:   0,
            });

            selectedProduct = null;
            $("order_product_input").value = "";
            renderTable();
        });

        // ── Tabela ────────────────────────────────────────────
        const renderTable = () => {
            const tbody = $("order_items_body");
            tbody.innerHTML = "";

            if (!items.length) {
                tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-3">
                    Nenhum produto adicionado</td></tr>`;
            } else {
                items.forEach((item, i) => {
                    const subtotal = item.unit_price * (1 - item.discount / 100) * item.quantity;
                    const tr = document.createElement("tr");
                    tr.innerHTML = `
                        <td>${item.name}</td>
                        <td>R$ ${fmt(item.unit_price)}</td>
                        <td>
                            <input type="number" min="1" value="${item.quantity}"
                                class="form-control form-control-sm"
                                onchange="window._order.update(${i}, 'quantity', this.value)">
                        </td>
                        <td>
                            <div class="input-group input-group-sm">
                                <input type="number" step="0.01" min="0" max="100"
                                    value="${item.discount}"
                                    class="form-control form-control-sm"
                                    onchange="window._order.update(${i}, 'discount', this.value)">
                                <span class="input-group-text">%</span>
                            </div>
                        </td>
                        <td class="fw-semibold">R$ ${fmt(subtotal)}</td>
                        <td>
                            <button type="button" class="btn btn-sm btn-outline-danger"
                                onclick="window._order.remove(${i})">✕</button>
                        </td>`;
                    tbody.appendChild(tr);
                });
            }

            const subtotal = items.reduce(
                (acc, i) => acc + i.unit_price * (1 - i.discount / 100) * i.quantity, 0
            );
            const freight = parseBrl($("order_freight_field").value);
            const total   = subtotal + freight;
            const downPct = parseFloat($("order_down_payment_field").value) || 0;

            $("order_total").textContent              = fmt(total);
            $("order_down_payment_value").textContent = fmt(total * downPct / 100);

            $("items_json_field").value = JSON.stringify(
                items.map(i => ({
                    product_id: i.product_id,
                    unit_price: i.unit_price,
                    quantity:   i.quantity,
                    discount:   i.discount,
                }))
            );
        };

        window._order = {
            update: (i, field, value) => {
                items[i][field] = field === "quantity"
                    ? Math.max(1, parseInt(value) || 1)
                    : parseFloat(value) || 0;
                renderTable();
            },
            remove: i => {
                items.splice(i, 1);
                renderTable();
            },
        };

        // ── Submit ────────────────────────────────────────────
        $("orderForm").addEventListener("submit", function (e) {
            e.preventDefault();

            if (!$("client_id").value) return alert("Selecione um cliente.");
            if (!items.length)         return alert("Adicione ao menos um produto.");

            const freightInput = $("order_freight_field");
            freightInput.value = parseBrl(freightInput.value).toFixed(2);

            const formData = new FormData(this);
            const btn      = this.querySelector("[type=submit]");
            btn.disabled    = true;
            btn.textContent = "Salvando...";

            fetch(CREATE_URL, {
                method:  "POST",
                headers: { "X-CSRFToken": formData.get("csrfmiddlewaretoken") },
                body:    formData,
            })
                .then(r => r.json())
                .then(data => {
                    if (data.success) location.reload();
                    else alert(
                        Object.values(data.errors || {}).flat().join("\n") ||
                        data.error || "Erro desconhecido."
                    );
                })
                .catch(() => alert("Erro inesperado."))
                .finally(() => {
                    btn.disabled    = false;
                    btn.textContent = "Criar Pedido";
                    freightInput.value = fmt(parseBrl(freightInput.value));
                });
        });

        // ── Eventos extras ────────────────────────────────────
        $("order_freight_field").addEventListener("input", renderTable);
        $("order_down_payment_field").addEventListener("input", renderTable);
        modal.addEventListener("hidden.bs.modal", reset);
        document.querySelectorAll('[data-bs-target="#createOrderModal"]')
            .forEach(btn => btn.addEventListener("click", reset));

        renderTable();
        console.log("✅ Order modal inicializado.");
    }

    document.addEventListener("DOMContentLoaded", initOrderModal);
    document.addEventListener("shown.bs.modal",   initOrderModal);
    setTimeout(initOrderModal, 800);
})();