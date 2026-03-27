(function () {
    let currentOrderPk = null;
    const modalEl      = document.getElementById('invoiceModal');

    // ── Abre o modal ─────────────────────────────────────────
    document.addEventListener('click', function (e) {
        const btn = e.target.closest('.open-invoice-btn');
        if (!btn) return;

        currentOrderPk = btn.dataset.id;
        document.getElementById('invoice-order-number').textContent = btn.dataset.number;

        const hasInvoice  = btn.dataset.hasInvoice === 'true';
        const formEl      = document.getElementById('invoice-form');
        const existingEl  = document.getElementById('invoice-existing');
        const submitBtn   = document.getElementById('invoice-submit-btn');

        if (hasInvoice) {
            // Mostra NF existente
            document.getElementById('invoice-existing-number').textContent = btn.dataset.invoiceNumber;
            document.getElementById('invoice-existing-date').textContent   = btn.dataset.invoiceDate;
            document.getElementById('invoice-existing-link').href          = btn.dataset.invoiceUrl;
            existingEl.classList.remove('d-none');
            formEl.classList.add('d-none');
            submitBtn.classList.add('d-none');
        } else {
            // Mostra formulário de upload
            existingEl.classList.add('d-none');
            formEl.classList.remove('d-none');
            submitBtn.classList.remove('d-none');
            // Limpa campos
            document.getElementById('invoice-number').value    = '';
            document.getElementById('invoice-issued-at').value = '';
            document.getElementById('invoice-file').value      = '';
        }

        bootstrap.Modal.getOrCreateInstance(modalEl).show();
    });

    // ── Submete a NF ─────────────────────────────────────────
    document.getElementById('invoice-submit-btn').addEventListener('click', function () {
        if (!currentOrderPk) return;

        const number   = document.getElementById('invoice-number').value.trim();
        const issuedAt = document.getElementById('invoice-issued-at').value;
        const file     = document.getElementById('invoice-file').files[0];

        if (!number || !issuedAt || !file) {
            alert('Preencha todos os campos obrigatórios.');
            return;
        }

        const btn = this;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Enviando...';

        const formData = new FormData();
        formData.append('number',    number);
        formData.append('issued_at', issuedAt);
        formData.append('file',      file);
        formData.append('csrfmiddlewaretoken',
            document.cookie.match(/csrftoken=([^;]+)/)?.[1] ?? '');

        fetch(`/vendas/orders/${currentOrderPk}/invoice/`, {
            method: 'POST',
            body:   formData,
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                // Atualiza badge de status na linha
                const statusCell = document.getElementById(`order-status-${currentOrderPk}`);
                if (statusCell) {
                    statusCell.innerHTML = `<span class="badge bg-info text-dark">${data.status_label}</span>`;
                }

                // Atualiza data-attributes do botão da linha
                const rowBtn = document.querySelector(`.action-menu-btn[data-id="${currentOrderPk}"]`);
                if (rowBtn) {
                    rowBtn.dataset.hasInvoice    = 'true';
                    rowBtn.dataset.invoiceNumber = data.invoice.number;
                    rowBtn.dataset.invoiceDate   = data.invoice.issued_at;
                    rowBtn.dataset.invoiceUrl    = data.invoice.file_url;
                }

                bootstrap.Modal.getInstance(modalEl).hide();
            } else {
                alert('Erro: ' + (data.error || 'Não foi possível anexar a NF.'));
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-upload me-1"></i> Anexar NF';
            }
        })
        .catch(() => {
            alert('Erro inesperado. Tente novamente.');
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-upload me-1"></i> Anexar NF';
        });
    });

    // ── Remove a NF ──────────────────────────────────────────
    document.getElementById('invoice-delete-btn').addEventListener('click', function () {
        if (!currentOrderPk) return;
        if (!confirm('Tem certeza que deseja remover a nota fiscal?')) return;

        const btn = this;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Removendo...';

        fetch(`/vendas/orders/${currentOrderPk}/invoice/delete/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.cookie.match(/csrftoken=([^;]+)/)?.[1] ?? '',
            },
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                // Atualiza badge de status na linha
                const statusCell = document.getElementById(`order-status-${currentOrderPk}`);
                if (statusCell) {
                    statusCell.innerHTML = `<span class="badge bg-success">${data.status_label}</span>`;
                }

                // Atualiza data-attributes do botão da linha
                const rowBtn = document.querySelector(`.action-menu-btn[data-id="${currentOrderPk}"]`);
                if (rowBtn) {
                    rowBtn.dataset.hasInvoice = 'false';
                    delete rowBtn.dataset.invoiceNumber;
                    delete rowBtn.dataset.invoiceDate;
                    delete rowBtn.dataset.invoiceUrl;
                }

                bootstrap.Modal.getInstance(modalEl).hide();
            } else {
                alert('Erro: ' + (data.error || 'Não foi possível remover a NF.'));
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-trash me-1"></i> Remover NF';
            }
        })
        .catch(() => {
            alert('Erro inesperado. Tente novamente.');
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-trash me-1"></i> Remover NF';
        });
    });

    // ── Reset ao fechar ───────────────────────────────────────
    modalEl.addEventListener('hidden.bs.modal', function () {
        currentOrderPk = null;
        document.getElementById('invoice-submit-btn').disabled = false;
        document.getElementById('invoice-submit-btn').innerHTML = '<i class="bi bi-upload me-1"></i> Anexar NF';
        document.getElementById('invoice-delete-btn').disabled = false;
        document.getElementById('invoice-delete-btn').innerHTML = '<i class="bi bi-trash me-1"></i> Remover NF';
    });

})();