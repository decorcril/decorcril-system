(function () {
    // ── Lê permissões do data-attribute ──────────────────────
    const perms       = document.getElementById('user-perms').dataset;
    const canPayment  = perms.canPayment  === 'true';
    const canAdvance  = perms.canAdvance  === 'true';
    const isSupervisor = perms.isSupervisor === 'true';
    const canEdit     = isSupervisor || (!canPayment && !canAdvance); // Vendedor pode editar

    // ── Menu flutuante ────────────────────────────────────────
    const menuEl = document.createElement('ul');
    menuEl.id = 'floating-action-menu';
    menuEl.className = 'dropdown-menu shadow';
    menuEl.style.cssText = 'position:fixed;z-index:99999;display:none;min-width:210px;';
    document.body.appendChild(menuEl);

    let currentId = null;

    function buildMenu(btn) {
        const id        = btn.dataset.id;
        const number    = btn.dataset.number;
        const pdfUrl    = btn.dataset.pdfUrl;
        const prodUrl   = btn.dataset.prodUrl;
        const canDelete = btn.dataset.canDelete === 'true';
        const canCancel = btn.dataset.canCancel === 'true';

        menuEl.innerHTML = `
            <li>
                <button class="dropdown-item open-view-order-btn" data-id="${id}">
                    <i class="bi bi-eye me-2 text-info"></i> Visualizar
                </button>
            </li>

            ${canPayment ? `
            <li>
                <button class="dropdown-item open-payments-btn" data-id="${id}" data-number="${number}">
                    <i class="bi bi-cash-coin me-2 text-success"></i> Pagamentos
                </button>
            </li>` : ''}

            ${canEdit ? `
            <li>
                <button class="dropdown-item open-edit-order-btn" data-id="${id}">
                    <i class="bi bi-pencil me-2 text-warning"></i> Editar
                </button>
            </li>` : ''}

            <li>
                <a class="dropdown-item" href="${pdfUrl}" target="_blank">
                    <i class="bi bi-file-earmark-pdf me-2 text-dark"></i> PDF do Pedido
                </a>
            </li>
            <li>
                <a class="dropdown-item" href="${prodUrl}" target="_blank">
                    <i class="bi bi-gear me-2 text-primary"></i> Ordem de Produção
                </a>
            </li>

            ${canCancel || canDelete ? '<li><hr class="dropdown-divider"></li>' : ''}

            ${canCancel ? `
            <li>
                <button class="dropdown-item text-danger cancel-order-btn" data-id="${id}" data-number="${number}">
                    <i class="bi bi-x-circle me-2"></i> Cancelar Pedido
                </button>
            </li>` : ''}

            ${canDelete ? `
            <li>
                <button class="dropdown-item text-danger trigger-delete-btn" data-id="${id}">
                    <i class="bi bi-trash me-2"></i> Excluir
                </button>
            </li>` : `
            <li>
                <button class="dropdown-item text-muted" disabled>
                    <i class="bi bi-trash me-2"></i> Excluir
                </button>
            </li>`}
        `;
    }

    function showMenu(btn) {
        currentId = btn.dataset.id;
        buildMenu(btn);
        menuEl.style.display = 'block';

        const rect      = btn.getBoundingClientRect();
        const menuW     = 210;
        const menuH     = menuEl.offsetHeight;
        const spaceDown = window.innerHeight - rect.bottom;
        const left      = Math.max(4, rect.right - menuW);

        if (spaceDown < menuH + 8) {
            menuEl.style.top = (rect.top - menuH - 4) + 'px';
        } else {
            menuEl.style.top = (rect.bottom + 4) + 'px';
        }

        menuEl.style.left = left + 'px';
    }

    function hideMenu() {
        menuEl.style.display = 'none';
        currentId = null;
    }

    document.addEventListener('click', function (e) {
        const btn = e.target.closest('.action-menu-btn');
        if (btn) {
            e.stopPropagation();
            if (menuEl.style.display === 'block' && currentId === btn.dataset.id) {
                hideMenu();
            } else {
                showMenu(btn);
            }
            return;
        }

        const delBtn = e.target.closest('.trigger-delete-btn');
        if (delBtn) {
            hideMenu();
            const modal = document.getElementById(`deleteOrderModal${delBtn.dataset.id}`);
            if (modal) bootstrap.Modal.getOrCreateInstance(modal).show();
            return;
        }

        if (!menuEl.contains(e.target)) hideMenu();
    });

    document.addEventListener('scroll', hideMenu, true);

    // ── Cancelar pedido ───────────────────────────────────────
    let cancelOrderPk = null;
    const cancelModalEl = document.getElementById('cancelOrderModal');

    document.addEventListener('click', function (e) {
        const btn = e.target.closest('.cancel-order-btn');
        if (!btn) return;

        cancelOrderPk = btn.dataset.id;
        document.getElementById('cancel-order-number').textContent = btn.dataset.number;

        hideMenu();
        bootstrap.Modal.getOrCreateInstance(cancelModalEl).show();
    });

    document.getElementById('cancelOrderBtn').addEventListener('click', function () {
        if (!cancelOrderPk) return;

        const btn = this;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Cancelando...';

        fetch(`/vendas/orders/${cancelOrderPk}/cancel/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.cookie.match(/csrftoken=([^;]+)/)?.[1] ?? '',
            },
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const statusCell = document.getElementById(`order-status-${cancelOrderPk}`);
                if (statusCell) {
                    statusCell.innerHTML = `<span class="badge bg-danger">${data.status_label}</span>`;
                }
                const rowBtn = document.querySelector(`.action-menu-btn[data-id="${cancelOrderPk}"]`);
                if (rowBtn) {
                    rowBtn.dataset.status    = 'canceled';
                    rowBtn.dataset.canCancel = 'false';
                    rowBtn.dataset.canDelete = 'true';
                }
                bootstrap.Modal.getInstance(cancelModalEl).hide();
            } else {
                alert('Erro: ' + (data.error || 'Não foi possível cancelar o pedido.'));
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-x-circle me-1"></i> Cancelar Pedido';
            }
        })
        .catch(() => {
            alert('Erro inesperado. Tente novamente.');
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-x-circle me-1"></i> Cancelar Pedido';
        });
    });

    cancelModalEl.addEventListener('hidden.bs.modal', function () {
        const btn = document.getElementById('cancelOrderBtn');
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-x-circle me-1"></i> Cancelar Pedido';
        cancelOrderPk = null;
    });

})();