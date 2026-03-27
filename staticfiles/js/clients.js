/**
 * clients.js
 * Lógica do modal de criação e edição de clientes.
 * Depende de: masks.js (deve ser carregado antes no HTML)
 */

document.addEventListener('DOMContentLoaded', function () {

    // =====================================================
    // MODAL DE CRIAR
    // =====================================================
    const modal = document.getElementById('createClientModal');
    if (modal) {
        initCreateModal(modal);
    }

    // =====================================================
    // MODAL DE EDITAR (AJAX)
    // =====================================================
    document.addEventListener('click', function (e) {
        const btn = e.target.closest('.btn-edit-client');
        if (!btn) return;

        const url = btn.dataset.url;
        if (!url) return;

        const anterior = document.getElementById('editClientModalContainer');
        if (anterior) anterior.remove();

        const container = document.createElement('div');
        container.id = 'editClientModalContainer';
        document.body.appendChild(container);

        fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(r => r.text())
            .then(html => {
                container.innerHTML = html;

                const modalEl = container.querySelector('.modal');
                if (!modalEl) return;

                const bsModal = new bootstrap.Modal(modalEl);
                bsModal.show();

                initEditModal(modalEl);

                modalEl.addEventListener('hidden.bs.modal', () => container.remove());
            })
            .catch(() => alert('Erro ao carregar o formulário de edição.'));
    });

});


// =====================================================
// INIT MODAL DE CRIAR
// =====================================================
function initCreateModal(modal) {

    const form        = modal.querySelector('#createClientForm');
    const personType  = modal.querySelector('#id_person_type');
    const docInput    = modal.querySelector('#id_document');
    const docLabel    = modal.querySelector('#label_document');
    const nameLabel   = modal.querySelector('#label_name');
    const zipInput    = modal.querySelector('#id_zip_code');
    const phoneInput  = modal.querySelector('#id_phone');
    const whatsInput  = modal.querySelector('#id_whatsapp');
    const streetInput = modal.querySelector('#id_street');
    const neighInput  = modal.querySelector('#id_neighborhood');
    const cityInput   = modal.querySelector('#id_city');
    const stateInput  = modal.querySelector('#id_state');
    const wrapTrade    = modal.querySelector('#wrap_trade_name');
    const wrapStateReg = modal.querySelector('#wrap_state_registration');
    const wrapMuniReg  = modal.querySelector('#wrap_municipal_registration');

    let docDuplicado = false;

    if (form) {
        form.addEventListener('keydown', function (e) {
            if (e.key !== 'Enter') return;
            if (e.target.tagName.toLowerCase() === 'textarea') return;
            e.preventDefault();
            if (e.target === zipInput) zipInput.dispatchEvent(new Event('blur'));
        });
    }

    function adaptarCampos(tipo) {
        const isPF = tipo === 'PF';
        const isPJ = tipo === 'PJ';

        if (nameLabel) {
            if (isPF)      nameLabel.innerHTML = 'Nome Completo <span class="text-danger">*</span>';
            else if (isPJ) nameLabel.innerHTML = 'Razão Social <span class="text-danger">*</span>';
            else           nameLabel.innerHTML = 'Nome / Razão Social <span class="text-danger">*</span>';
        }

        if (docLabel && docInput) {
            if (isPF) {
                docLabel.innerHTML = 'CPF <span class="text-danger">*</span>';
                docInput.placeholder = '000.000.000-00';
            } else if (isPJ) {
                docLabel.innerHTML = 'CNPJ <span class="text-danger">*</span>';
                docInput.placeholder = '00.000.000/0000-00';
            } else {
                docLabel.innerHTML = 'CPF / CNPJ <span class="text-danger">*</span>';
                docInput.placeholder = 'Selecione o tipo de pessoa';
            }
        }

        [wrapTrade, wrapStateReg, wrapMuniReg].forEach(wrap => {
            if (!wrap) return;
            wrap.style.display = isPF ? 'none' : '';
            if (isPF) wrap.querySelectorAll('input').forEach(i => i.value = '');
        });
    }

    modal.addEventListener('show.bs.modal', function () {
        if (!form) return;
        form.reset();
        modal.querySelector('#id_is_active').checked   = true;
        modal.querySelector('#id_is_supplier').checked = false;
        modal.querySelector('#id_is_carrier').checked  = false;
        modal.querySelector('#id_is_partner').checked  = false;
        if (docInput) docInput.classList.remove('is-valid', 'is-invalid');
        modal.querySelectorAll('.doc-feedback').forEach(el => el.remove());
        docDuplicado = false;
        adaptarCampos('');
    });

    if (personType) {
        personType.addEventListener('change', function () {
            if (docInput) {
                docInput.value = '';
                docInput.classList.remove('is-valid', 'is-invalid');
            }
            modal.querySelectorAll('.doc-feedback').forEach(el => el.remove());
            docDuplicado = false;
            adaptarCampos(this.value);
        });
    }

    adaptarCampos(personType?.value || '');

    function validarCPF(cpf) {
        cpf = cpf.replace(/\D/g, '');
        if (cpf.length !== 11 || /^(\d)\1{10}$/.test(cpf)) return false;
        let soma = 0;
        for (let i = 0; i < 9; i++) soma += parseInt(cpf[i]) * (10 - i);
        let resto = (soma * 10) % 11;
        if (resto === 10 || resto === 11) resto = 0;
        if (resto !== parseInt(cpf[9])) return false;
        soma = 0;
        for (let i = 0; i < 10; i++) soma += parseInt(cpf[i]) * (11 - i);
        resto = (soma * 10) % 11;
        if (resto === 10 || resto === 11) resto = 0;
        return resto === parseInt(cpf[10]);
    }

    function validarCNPJ(cnpj) {
        cnpj = cnpj.replace(/\D/g, '');
        if (cnpj.length !== 14 || /^(\d)\1{13}$/.test(cnpj)) return false;
        const calc = (cnpj, pesos) => {
            let soma = 0;
            for (let i = 0; i < pesos.length; i++) soma += parseInt(cnpj[i]) * pesos[i];
            const resto = soma % 11;
            return resto < 2 ? 0 : 11 - resto;
        };
        return calc(cnpj, [5,4,3,2,9,8,7,6,5,4,3,2]) === parseInt(cnpj[12]) &&
               calc(cnpj, [6,5,4,3,2,9,8,7,6,5,4,3,2]) === parseInt(cnpj[13]);
    }

    function setDocFeedback(valido, mensagem) {
        docInput.classList.remove('is-valid', 'is-invalid');
        modal.querySelectorAll('.doc-feedback').forEach(el => el.remove());
        docInput.classList.add(valido ? 'is-valid' : 'is-invalid');
        const msg = document.createElement('div');
        msg.className = `doc-feedback ${valido ? 'valid-feedback' : 'invalid-feedback'}`;
        msg.textContent = mensagem;
        docInput.parentNode.appendChild(msg);
    }

    function verificarDuplicidade(document) {
        const tipo = personType?.value;
        if (!tipo) return;
        fetch(`/clientes/verificar-documento/?document=${encodeURIComponent(document)}`)
            .then(r => r.json())
            .then(data => {
                if (data.exists) {
                    docDuplicado = true;
                    setDocFeedback(false, `Já cadastrado como "${data.name}".`);
                } else {
                    docDuplicado = false;
                    setDocFeedback(true, `${tipo === 'PF' ? 'CPF' : 'CNPJ'} válido.`);
                }
            })
            .catch(() => { docDuplicado = false; });
    }

    if (docInput) {
        Masks.aplicar(docInput, 'documento', () => personType?.value);
        docInput.addEventListener('input', function () {
            this.classList.remove('is-valid', 'is-invalid');
            modal.querySelectorAll('.doc-feedback').forEach(el => el.remove());
            docDuplicado = false;
        });
        docInput.addEventListener('blur', function () {
            const tipo = personType?.value;
            if (!tipo || !this.value) return;
            const numeros = this.value.replace(/\D/g, '');
            const valido = tipo === 'PF' ? validarCPF(numeros) : validarCNPJ(numeros);
            if (!valido) {
                setDocFeedback(false, `${tipo === 'PF' ? 'CPF' : 'CNPJ'} inválido. Verifique os dígitos.`);
                docDuplicado = false;
                return;
            }
            verificarDuplicidade(this.value);
        });
    }

    if (form) {
        form.addEventListener('submit', function (e) {
            const tipo = personType?.value;
            if (!tipo || !docInput?.value) return;
            const numeros = docInput.value.replace(/\D/g, '');
            const valido = tipo === 'PF' ? validarCPF(numeros) : validarCNPJ(numeros);
            if (!valido) {
                e.preventDefault();
                setDocFeedback(false, `${tipo === 'PF' ? 'CPF' : 'CNPJ'} inválido. Verifique os dígitos.`);
                docInput.focus();
                return;
            }
            if (docDuplicado) {
                e.preventDefault();
                docInput.focus();
            }
        });
    }

    Masks.aplicar(zipInput, 'cep');
    Masks.autocepBind(zipInput, {
        street: streetInput, neighborhood: neighInput,
        city: cityInput, state: stateInput,
        focusAfter: modal.querySelector('#id_number'),
    });
    Masks.aplicar(phoneInput, 'phone');
    Masks.aplicar(whatsInput, 'whatsapp');
}


// =====================================================
// INIT MODAL DE EDITAR
// =====================================================
function initEditModal(modalEl) {

    const form        = modalEl.querySelector('form');
    const url         = form?.dataset.url || form?.action;
    const personType  = modalEl.querySelector('#id_person_type');
    const docInput    = modalEl.querySelector('#id_document');
    const docLabel    = modalEl.querySelector('#label_document');
    const nameLabel   = modalEl.querySelector('#label_name');
    const zipInput    = modalEl.querySelector('#id_zip_code');
    const phoneInput  = modalEl.querySelector('#id_phone');
    const whatsInput  = modalEl.querySelector('#id_whatsapp');
    const streetInput = modalEl.querySelector('#id_street');
    const neighInput  = modalEl.querySelector('#id_neighborhood');
    const cityInput   = modalEl.querySelector('#id_city');
    const stateInput  = modalEl.querySelector('#id_state');
    const wrapTrade    = modalEl.querySelector('#wrap_trade_name');
    const wrapStateReg = modalEl.querySelector('#wrap_state_registration');
    const wrapMuniReg  = modalEl.querySelector('#wrap_municipal_registration');

    function adaptarCampos(tipo) {
        const isPF = tipo === 'PF';
        const isPJ = tipo === 'PJ';

        if (nameLabel) {
            if (isPF)      nameLabel.innerHTML = 'Nome Completo <span class="text-danger">*</span>';
            else if (isPJ) nameLabel.innerHTML = 'Razão Social <span class="text-danger">*</span>';
        }

        if (docLabel) {
            if (isPF)      docLabel.innerHTML = 'CPF <span class="text-danger">*</span>';
            else if (isPJ) docLabel.innerHTML = 'CNPJ <span class="text-danger">*</span>';
        }

        [wrapTrade, wrapStateReg, wrapMuniReg].forEach(wrap => {
            if (!wrap) return;
            wrap.style.display = isPF ? 'none' : '';
        });
    }

    if (personType) {
        adaptarCampos(personType.value);
        personType.addEventListener('change', function () {
            adaptarCampos(this.value);
        });
    }

    Masks.aplicar(zipInput, 'cep');
    Masks.autocepBind(zipInput, {
        street: streetInput, neighborhood: neighInput,
        city: cityInput, state: stateInput,
        focusAfter: modalEl.querySelector('#id_number'),
    });
    Masks.aplicar(phoneInput, 'phone');
    Masks.aplicar(whatsInput, 'whatsapp');

    if (docInput && !docInput.disabled) {
        Masks.aplicar(docInput, 'documento', () => personType?.value);
    }

    if (form) {
        form.addEventListener('keydown', function (e) {
            if (e.key !== 'Enter') return;
            if (e.target.tagName.toLowerCase() === 'textarea') return;
            e.preventDefault();
            if (e.target === zipInput) zipInput.dispatchEvent(new Event('blur'));
        });
    }

    // --------------------------------------------------
    // Submit via AJAX
    // --------------------------------------------------
    if (form) {
        form.addEventListener('submit', function (e) {
            e.preventDefault();

            const formData = new FormData(form);

            fetch(url, {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {

                    // 1. Atualiza a row na tabela
                    const row = document.getElementById(`client-row-${data.client_id}`);
                    if (row && data.row_html) row.outerHTML = data.row_html;

                    // 2. Substitui os modais de visualização e edição no container
                    const modalsContainer = document.getElementById(`client-modals-${data.client_id}`);
                    if (modalsContainer && data.modals_html) {
                        // Destroi instâncias Bootstrap antes de remover os elementos do DOM
                        modalsContainer.querySelectorAll('.modal').forEach(m => {
                            const instance = bootstrap.Modal.getInstance(m);
                            if (instance) instance.dispose();
                        });
                        modalsContainer.innerHTML = data.modals_html;
                    }

                    // 3. Fecha e destroi o modal de edição
                    const editInstance = bootstrap.Modal.getInstance(modalEl);
                    if (editInstance) {
                        modalEl.addEventListener('hidden.bs.modal', () => {}, { once: true });
                        editInstance.hide();
                    }

                } else {
                    const container = document.getElementById('editClientModalContainer');
                    if (container) {
                        container.innerHTML = data.html;
                        const newModal = container.querySelector('.modal');
                        if (newModal) {
                            new bootstrap.Modal(newModal).show();
                            initEditModal(newModal);
                            newModal.addEventListener('hidden.bs.modal', () => container.remove());
                        }
                    }
                }
            })
            .catch(() => alert('Erro ao salvar. Tente novamente.'));
        });
    }
}