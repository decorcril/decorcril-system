(function () {
    let currentOrderPk = null;
    const modalEl      = document.getElementById('shipmentModal');

    // ── Abre o modal ─────────────────────────────────────────
    document.addEventListener('click', function (e) {
        const btn = e.target.closest('.open-shipment-btn');
        if (!btn) return;

        currentOrderPk = btn.dataset.id;
        document.getElementById('shipment-order-number').textContent = btn.dataset.number;

        const hasShipment = btn.dataset.hasShipment === 'true';
        const formEl      = document.getElementById('shipment-form');
        const existingEl  = document.getElementById('shipment-existing');
        const submitBtn   = document.getElementById('shipment-submit-btn');

        if (hasShipment) {
            document.getElementById('shipment-existing-carrier').textContent  = btn.dataset.shipmentCarrier  || '—';
            document.getElementById('shipment-existing-tracking').textContent = btn.dataset.shipmentTracking || '—';
            document.getElementById('shipment-existing-date').textContent     = btn.dataset.shipmentDate     || '—';
            document.getElementById('shipment-existing-link').href            = btn.dataset.shipmentUrl      || '#';
            existingEl.classList.remove('d-none');
            formEl.classList.add('d-none');
            submitBtn.classList.add('d-none');
        } else {
            existingEl.classList.add('d-none');
            formEl.classList.remove('d-none');
            submitBtn.classList.remove('d-none');
            document.getElementById('shipment-carrier').value  = '';
            document.getElementById('shipment-tracking').value = '';
            document.getElementById('shipment-file').value     = '';
        }

        bootstrap.Modal.getOrCreateInstance(modalEl).show();
    });

    // ── Submete o envio ───────────────────────────────────────
    document.getElementById('shipment-submit-btn').addEventListener('click', function () {
        if (!currentOrderPk) return;

        const carrier  = document.getElementById('shipment-carrier').value.trim();
        const tracking = document.getElementById('shipment-tracking').value.trim();
        const file     = document.getElementById('shipment-file').files[0];

        if (!file) {
            alert('Anexe o comprovante de envio.');
            return;
        }

        const btn = this;
        btn.disabled  = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Enviando...';

        const formData = new FormData();
        formData.append('carrier',  carrier);
        formData.append('tracking', tracking);
        formData.append('file',     file);
        formData.append('csrfmiddlewaretoken',
            document.cookie.match(/csrftoken=([^;]+)/)?.[1] ?? '');

        fetch(`/vendas/orders/${currentOrderPk}/shipment/`, {
            method: 'POST',
            body:   formData,
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const statusCell = document.getElementById(`order-status-${currentOrderPk}`);
                if (statusCell) {
                    statusCell.innerHTML = `<span class="badge bg-primary">${data.status_label}</span>`;
                }

                const rowBtn = document.querySelector(`.action-menu-btn[data-id="${currentOrderPk}"]`);
                if (rowBtn) {
                    rowBtn.dataset.hasShipment      = 'true';
                    rowBtn.dataset.shipmentCarrier  = data.shipment.carrier;
                    rowBtn.dataset.shipmentTracking = data.shipment.tracking;
                    rowBtn.dataset.shipmentDate     = data.shipment.created_at;
                    rowBtn.dataset.shipmentUrl      = data.shipment.file_url;
                }

                bootstrap.Modal.getInstance(modalEl).hide();
            } else {
                alert('Erro: ' + (data.error || 'Não foi possível registrar o envio.'));
                btn.disabled  = false;
                btn.innerHTML = '<i class="bi bi-truck me-1"></i> Registrar Envio';
            }
        })
        .catch(() => {
            alert('Erro inesperado. Tente novamente.');
            btn.disabled  = false;
            btn.innerHTML = '<i class="bi bi-truck me-1"></i> Registrar Envio';
        });
    });

    // ── Remove o envio ────────────────────────────────────────
    document.getElementById('shipment-delete-btn').addEventListener('click', function () {
        if (!currentOrderPk) return;
        if (!confirm('Tem certeza que deseja remover o comprovante de envio?')) return;

        const btn = this;
        btn.disabled  = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Removendo...';

        fetch(`/vendas/orders/${currentOrderPk}/shipment/delete/`, {
            method:  'POST',
            headers: {
                'X-CSRFToken': document.cookie.match(/csrftoken=([^;]+)/)?.[1] ?? '',
            },
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const statusCell = document.getElementById(`order-status-${currentOrderPk}`);
                if (statusCell) {
                    statusCell.innerHTML = `<span class="badge bg-info text-dark">${data.status_label}</span>`;
                }

                const rowBtn = document.querySelector(`.action-menu-btn[data-id="${currentOrderPk}"]`);
                if (rowBtn) {
                    rowBtn.dataset.hasShipment = 'false';
                    delete rowBtn.dataset.shipmentCarrier;
                    delete rowBtn.dataset.shipmentTracking;
                    delete rowBtn.dataset.shipmentDate;
                    delete rowBtn.dataset.shipmentUrl;
                }

                bootstrap.Modal.getInstance(modalEl).hide();
            } else {
                alert('Erro: ' + (data.error || 'Não foi possível remover o envio.'));
                btn.disabled  = false;
                btn.innerHTML = '<i class="bi bi-trash me-1"></i> Remover Envio';
            }
        })
        .catch(() => {
            alert('Erro inesperado. Tente novamente.');
            btn.disabled  = false;
            btn.innerHTML = '<i class="bi bi-trash me-1"></i> Remover Envio';
        });
    });

    // ── Reset ao fechar ───────────────────────────────────────
    modalEl.addEventListener('hidden.bs.modal', function () {
        currentOrderPk = null;
        const submitBtn = document.getElementById('shipment-submit-btn');
        submitBtn.disabled  = false;
        submitBtn.innerHTML = '<i class="bi bi-truck me-1"></i> Registrar Envio';
        const deleteBtn = document.getElementById('shipment-delete-btn');
        deleteBtn.disabled  = false;
        deleteBtn.innerHTML = '<i class="bi bi-trash me-1"></i> Remover Envio';
    });

})();