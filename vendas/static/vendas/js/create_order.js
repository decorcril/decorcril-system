(function () {
    "use strict";

    function initOrderModal() {
        const modal = document.getElementById("createOrderModal");
        if (!modal || modal._orderInitialized) return;
        modal._orderInitialized = true;

        const ORDER_CLIENT_URL  = document.getElementById("client_input").dataset.url;
        const ORDER_PRODUCT_URL = document.getElementById("order_product_input").dataset.url;
        const ORDER_CREATE_URL  = document.getElementById("orderForm").dataset.url;

        let orderItems = [];
        let selectedOrderProduct = null;

        const getO = id => document.getElementById(id);
        const fmtO = v => parseFloat(v || 0).toLocaleString("pt-BR", { minimumFractionDigits: 2 });

        // ================= RESET =================
        const resetModal = () => {
            orderItems = [];
            selectedOrderProduct = null;
            getO("client_input").value = "";
            getO("client_id").value = "";
            getO("client_results").classList.add("d-none");
            getO("order_product_input").value = "";
            getO("order_product_results").classList.add("d-none");
            getO("order_down_payment_field").value = "0";
            getO("order_freight_field").value = "0";
            renderOrder();
        };

        const showClientInfo = c => {
            document.getElementById("client_info_name").textContent     = c.text;
            document.getElementById("client_info_document").textContent = c.detail || "";
            document.getElementById("client_info_badge").textContent    = c.badge || "";

            const phone = document.getElementById("client_info_phone");
            const phoneWrap = document.getElementById("client_info_phone_wrap");
            phone.textContent = c.phone || "";
            phoneWrap.classList.toggle("d-none", !c.phone);

            const email = document.getElementById("client_info_email");
            const emailWrap = document.getElementById("client_info_email_wrap");
            email.textContent = c.email || "";
            emailWrap.classList.toggle("d-none", !c.email);

            const address = document.getElementById("client_info_address");
            const addressWrap = document.getElementById("client_info_address_wrap");
            address.textContent = c.address || "";
            addressWrap.classList.toggle("d-none", !c.address);

            document.getElementById("client_info_card").classList.remove("d-none");
        };

        const hideClientInfo = () => {
            document.getElementById("client_info_card").classList.add("d-none");
        };

        // ================= CLIENTE =================
        const renderClientResults = data => {
            const box = getO("client_results");
            box.innerHTML = "";
            if (!data.length) { box.classList.add("d-none"); return; }

            data.forEach(c => {
                const a = document.createElement("a");
                a.href = "#";
                a.className = "list-group-item list-group-item-action";
                a.innerHTML = `<div class="fw-semibold">${c.text}</div><small class="text-muted">${c.detail || ""}</small>`;
                a.onclick = e => {
                    e.preventDefault();
                    getO("client_input").value = c.text;
                    getO("client_id").value = c.id;
                    box.classList.add("d-none");
                    showClientInfo(c);
                };
                box.appendChild(a);
            });
            box.classList.remove("d-none");
        };

        const searchClientOrder = () => {
            const term = getO("client_input").value.trim();
            if (term.length < 2) return;
            fetch(`${ORDER_CLIENT_URL}?q=${encodeURIComponent(term)}`)
                .then(r => r.json())
                .then(renderClientResults)
                .catch(err => console.error("Erro cliente:", err));
        };

        const clearClientOrder = () => {
            getO("client_input").value = "";
            getO("client_id").value = "";
            getO("client_results").classList.add("d-none");
            hideClientInfo();
        };

        getO("btn_search_client").addEventListener("click", searchClientOrder);
        getO("btn_clear_client").addEventListener("click", clearClientOrder);
        getO("client_input").addEventListener("keyup", function () {
            if (this.value.trim().length >= 2) searchClientOrder();
            else getO("client_results").classList.add("d-none");
        });

        // ================= PRODUTO =================
        const renderProductResults = data => {
            const box = getO("order_product_results");
            box.innerHTML = "";
            if (!data.length) { box.classList.add("d-none"); return; }

            data.forEach(p => {
                const a = document.createElement("a");
                a.href = "#";
                a.className = "list-group-item list-group-item-action";
                a.innerHTML = `${p.text} <small class="text-muted ms-2">${p.sku || ""} · R$ ${fmtO(p.price)}</small>`;
                a.onclick = e => {
                    e.preventDefault();
                    selectedOrderProduct = p;
                    getO("order_product_input").value = p.text;
                    box.classList.add("d-none");
                };
                box.appendChild(a);
            });
            box.classList.remove("d-none");
        };

        const searchProductOrder = () => {
            const term = getO("order_product_input").value.trim();
            if (term.length < 2) return;
            fetch(`${ORDER_PRODUCT_URL}?q=${encodeURIComponent(term)}`)
                .then(r => r.json())
                .then(renderProductResults)
                .catch(err => console.error("Erro produto:", err));
        };

        getO("btn_search_product").addEventListener("click", searchProductOrder);
        getO("order_product_input").addEventListener("keyup", function () {
            if (this.value.trim().length >= 2) searchProductOrder();
            else getO("order_product_results").classList.add("d-none");
        });

        const addProductOrder = () => {
            if (!selectedOrderProduct) return;
            if (orderItems.find(i => i.product_id === selectedOrderProduct.id)) {
                selectedOrderProduct = null;
                getO("order_product_input").value = "";
                return;
            }
            orderItems.push({
                product_id: selectedOrderProduct.id,
                name: selectedOrderProduct.text,
                unit_price: parseFloat(selectedOrderProduct.price) || 0,
                quantity: 1,
                discount: 0
            });
            selectedOrderProduct = null;
            getO("order_product_input").value = "";
            renderOrder();
        };

        getO("btn_add_product").addEventListener("click", addProductOrder);

        // ================= TABELA E TOTAL =================
        const renderOrder = () => {
            const tbody = getO("order_items_body");
            tbody.innerHTML = "";

            if (!orderItems.length) {
                tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-3">Nenhum produto adicionado</td></tr>`;
            } else {
                orderItems.forEach((item, i) => {
                    const tr = document.createElement("tr");
                    tr.innerHTML = `
                        <td>${item.name}</td>
                        <td>R$ ${fmtO(item.unit_price)}</td>
                        <td><input type="number" min="1" value="${item.quantity}" class="form-control form-control-sm" onchange="updateOrderItem(${i}, 'quantity', this.value)"></td>
                        <td><div class="input-group input-group-sm"><input type="number" step="0.01" min="0" max="100" value="${item.discount}" class="form-control form-control-sm" onchange="updateOrderItem(${i}, 'discount', this.value)"><span class="input-group-text">%</span></div></td>
                        <td class="fw-semibold">R$ ${fmtO(item.unit_price * (1 - (item.discount || 0) / 100) * item.quantity)}</td>
                        <td><button type="button" class="btn btn-sm btn-outline-danger" onclick="removeOrderItem(${i})">✕</button></td>
                    `;
                    tbody.appendChild(tr);
                });
            }

            const subtotal = orderItems.reduce((acc, i) => acc + i.unit_price * (1 - (i.discount || 0) / 100) * i.quantity, 0);
            const freight  = parseFloat(getO("order_freight_field").value) || 0;
            const total    = subtotal + freight;
            const downPct  = parseFloat(getO("order_down_payment_field").value) || 0;

            getO("order_total").textContent              = fmtO(total);
            getO("order_down_payment_value").textContent = fmtO(total * (downPct / 100));
            getO("items_json_field").value               = JSON.stringify(orderItems);
        };

        window.updateOrderItem = (i, field, value) => {
            orderItems[i][field] = field === "quantity" ? Math.max(1, parseInt(value) || 1) : parseFloat(value) || 0;
            renderOrder();
        };

        window.removeOrderItem = (i) => {
            orderItems.splice(i, 1);
            renderOrder();
        };

        // ================= SUBMIT =================
        getO("orderForm").addEventListener("submit", function (e) {
            e.preventDefault();
            if (!getO("client_id").value) return alert("Selecione um cliente.");
            if (!orderItems.length)       return alert("Adicione ao menos um produto.");

            const formData = new FormData(this);
            const btn = this.querySelector("[type=submit]");
            btn.disabled    = true;
            btn.textContent = "Salvando...";

            fetch(ORDER_CREATE_URL, {
                method: "POST",
                headers: { "X-CSRFToken": formData.get("csrfmiddlewaretoken") },
                body: formData
            })
                .then(r => r.json())
                .then(data => {
                    if (data.success) location.reload();
                    else alert(Object.values(data.errors || {}).flat().join("\n") || data.error || "Erro desconhecido.");
                })
                .catch(() => alert("Erro inesperado."))
                .finally(() => { btn.disabled = false; btn.textContent = "Criar Pedido"; });
        });

        // ================= EVENTOS EXTRA =================
        getO("order_freight_field").addEventListener("input", renderOrder);
        getO("order_down_payment_field").addEventListener("input", renderOrder);

        // Reset ao fechar o modal
        modal.addEventListener("hidden.bs.modal", resetModal);

        // Botão que abre o modal também faz reset
        document.querySelectorAll('[data-bs-target="#createOrderModal"]').forEach(btn => {
            btn.addEventListener("click", resetModal);
        });

        renderOrder();
        console.log("✅ Order modal inicializado com sucesso.");
    }

    // 3 estratégias de inicialização para garantir que funcione
    document.addEventListener("DOMContentLoaded", initOrderModal);
    document.addEventListener("shown.bs.modal", initOrderModal);
    setTimeout(initOrderModal, 800);

})();