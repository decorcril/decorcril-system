/**
 * masks.js
 * Máscaras e formatações reutilizáveis em qualquer modal/formulário.
 * Uso: Masks.cpf(valor), Masks.aplicar(input, 'cep'), Masks.brl(1250) → 'R$ 1.250,00'
 */

const Masks = (() => {

    /* =========================
       FORMATADORES (string → string)
    ========================= */

    function cpf(v) {
        v = v.replace(/\D/g, '').slice(0, 11);
        v = v.replace(/(\d{3})(\d)/,       '$1.$2');
        v = v.replace(/(\d{3})(\d)/,       '$1.$2');
        v = v.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
        return v;
    }

    function cnpj(v) {
        v = v.replace(/\D/g, '').slice(0, 14);
        v = v.replace(/^(\d{2})(\d)/,              '$1.$2');
        v = v.replace(/^(\d{2})\.(\d{3})(\d)/,     '$1.$2.$3');
        v = v.replace(/\.(\d{3})(\d)/,              '.$1/$2');
        v = v.replace(/(\d{4})(\d)/,                '$1-$2');
        return v;
    }

    function cep(v) {
        v = v.replace(/\D/g, '').slice(0, 8);
        if (v.length > 5) v = v.replace(/(\d{5})(\d)/, '$1-$2');
        return v;
    }

    function phone(v) {
        v = v.replace(/\D/g, '').slice(0, 10);
        if (v.length > 6) v = v.replace(/(\d{2})(\d{4})(\d)/, '($1) $2-$3');
        else if (v.length > 2) v = v.replace(/(\d{2})(\d)/, '($1) $2');
        return v;
    }

    function whatsapp(v) {
        v = v.replace(/\D/g, '').slice(0, 11);
        if (v.length > 7) v = v.replace(/(\d{2})(\d{5})(\d)/, '($1) $2-$3');
        else if (v.length > 2) v = v.replace(/(\d{2})(\d)/, '($1) $2');
        return v;
    }

    function documento(v, tipo) {
        return tipo === 'PF' ? cpf(v) : cnpj(v);
    }

    /* =========================
       MOEDA BRASILEIRA
       Masks.brl(1250)     → 'R$ 1.250,00'
       Masks.brl('1250.5') → 'R$ 1.250,50'
       Masks.brl(null)     → 'R$ 0,00'
    ========================= */
    function brl(valor) {
        if (valor === null || valor === undefined || valor === '') return 'R$ 0,00';
        const num = parseFloat(valor);
        if (isNaN(num)) return 'R$ 0,00';
        return 'R$ ' + num.toFixed(2)
            .replace('.', ',')
            .replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    }

    /* =========================
       ENTRADA MONETÁRIA (digita e formata em tempo real)
       Masks.aplicar(inputEl, 'brl_input')
       Resultado: usuário digita 1250 → exibe 1.250,00
    ========================= */
    function brl_input(v) {
        // Remove tudo que não é dígito
        const digits = v.replace(/\D/g, '');
        if (!digits) return '0,00';
        const num = parseInt(digits, 10) / 100;
        return num.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    /* =========================
       APLICAR MÁSCARA A UM INPUT
       Masks.aplicar(inputEl, 'cep')
       Masks.aplicar(inputEl, 'documento', () => personType.value)
    ========================= */
    function aplicar(input, tipo, getTipo) {
        if (!input) return;

        const handlers = {
            cpf:       () => { input.value = cpf(input.value); },
            cnpj:      () => { input.value = cnpj(input.value); },
            cep:       () => { input.value = cep(input.value); },
            phone:     () => { input.value = phone(input.value); },
            whatsapp:   () => { input.value = whatsapp(input.value); },
            documento:  () => { input.value = documento(input.value, getTipo ? getTipo() : ''); },
            brl_input:  () => { input.value = brl_input(input.value); },
        };

        const fn = handlers[tipo];
        if (fn) input.addEventListener('input', fn);
    }

    /* =========================
       AUTOCOMPLETE CEP (ViaCEP)
       Masks.autocepBind(inputEl, { street, neighborhood, city, state })
    ========================= */
    function autocepBind(zipInput, campos) {
        if (!zipInput) return;

        zipInput.addEventListener('blur', function () {
            const cepNum = this.value.replace(/\D/g, '');
            if (cepNum.length !== 8) return;

            fetch(`https://viacep.com.br/ws/${cepNum}/json/`)
                .then(r => r.json())
                .then(data => {
                    if (data.erro) return;
                    if (campos.street)       campos.street.value       = data.logradouro || '';
                    if (campos.neighborhood) campos.neighborhood.value = data.bairro     || '';
                    if (campos.city)         campos.city.value         = data.localidade || '';
                    if (campos.state)        campos.state.value        = data.uf         || '';
                    if (campos.focusAfter)   campos.focusAfter.focus();
                })
                .catch(() => {});
        });
    }

    /* =========================
       FORMATAR VALOR ESTÁTICO (para exibição, sem input)
       Masks.formatar('12345678901', 'cpf') → '123.456.789-01'
    ========================= */
    function formatar(valor, tipo) {
        if (!valor) return valor;
        const map = { cpf, cnpj, cep, phone, whatsapp };
        return map[tipo] ? map[tipo](valor) : valor;
    }

    return { cpf, cnpj, cep, phone, whatsapp, documento, aplicar, autocepBind, formatar, brl, brl_input };

})();