// catalogo/static/catalogo/js/edit_product_modal.js

(function () {

    // Converte dígitos digitados → "1.250,00"
    function formatBR(v) {
        const d = v.replace(/\D/g, '');
        if (!d) return '';
        return (parseInt(d, 10) / 100).toFixed(2)
            .replace('.', ',')
            .replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    }

    // "1.250,00" → "1250.00" para o backend
    function parseBR(v) {
        return v ? v.replace(/\./g, '').replace(',', '.') : '';
    }

    // "1250.00" (ponto decimal garantido pelo numeric_fields) → "1.250,00"
    function fromBackend(v) {
        if (!v) return '';
        const num = parseFloat(v);
        if (!num) return '';
        return num.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    // Vincula máscara uma única vez por elemento
    function applyMask(display, hidden) {
        if (!display || !hidden || display._masked) return;
        display._masked = true;
        display.addEventListener('input', function () {
            const fmt  = formatBR(this.value);
            this.value   = fmt;
            hidden.value = parseBR(fmt);
        });
        display.addEventListener('blur', function () {
            if (!this.value) hidden.value = '';
        });
    }

    const FIELDS = [
        { f: 'base_price',   k: 'basePrice'   },
        { f: 'height_cm',    k: 'heightCm'    },
        { f: 'width_cm',     k: 'widthCm'     },
        { f: 'length_cm',    k: 'lengthCm'    },
        { f: 'diameter_cm',  k: 'diameterCm'  },
        { f: 'depth_cm',     k: 'depthCm'     },
        { f: 'curvature_cm', k: 'curvatureCm' },
    ];

    function initModal(modal) {
        const pid = modal.dataset.productId;
        if (!pid || modal._editInit) return;
        modal._editInit = true;

        // Vincula máscaras uma vez
        FIELDS.forEach(({ f }) => {
            applyMask(
                document.getElementById(f + '_display_edit_' + pid),
                document.getElementById(f + '_value_edit_'   + pid)
            );
        });

        // Ao abrir: preenche valores
        modal.addEventListener('show.bs.modal', function () {
            FIELDS.forEach(({ f, k }) => {
                const display = document.getElementById(f + '_display_edit_' + pid);
                const hidden  = document.getElementById(f + '_value_edit_'   + pid);
                if (!display || !hidden) return;
                const fmt     = fromBackend(modal.dataset[k]);
                display.value = fmt;
                hidden.value  = fmt ? parseBR(fmt) : '';
            });
        });

        // Ao fechar: limpa
        modal.addEventListener('hidden.bs.modal', function () {
            FIELDS.forEach(({ f }) => {
                const d = document.getElementById(f + '_display_edit_' + pid);
                const h = document.getElementById(f + '_value_edit_'   + pid);
                if (d) d.value = '';
                if (h) h.value = '';
            });
            const prev = document.getElementById('imagePreviewEdit' + pid);
            if (prev) prev.style.display = 'none';
        });
    }

    // Inicializa todos os modais de edição presentes na página
    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('.modal[data-product-id]').forEach(initModal);
    });

    // ── Helpers globais ───────────────────────────────────────
    window.previewEditImage = function (event, pid) {
        const reader = new FileReader();
        reader.onload = () => {
            const img = document.getElementById('previewImageEdit' + pid);
            const box = document.getElementById('imagePreviewEdit' + pid);
            if (img && box) { img.src = reader.result; box.style.display = 'block'; }
        };
        if (event.target.files[0]) reader.readAsDataURL(event.target.files[0]);
    };

    window.togglePriceFieldEdit = function (pid, checked) {
        const wrap    = document.getElementById('priceFieldEdit' + pid);
        const hidden  = document.getElementById('base_price_value_edit_' + pid);
        const display = document.getElementById('base_price_display_edit_' + pid);
        if (!wrap) return;
        wrap.style.display = checked ? 'block' : 'none';
        if (hidden) hidden.required = checked;
        if (!checked) {
            if (display) display.value = '';
            if (hidden)  hidden.value  = '';
        }
    };

    window.toggleElectricalFieldsEdit = function (pid, checked) {
        const wrap = document.getElementById('electricalFieldsEdit' + pid);
        if (!wrap) return;
        wrap.style.display = checked ? 'block' : 'none';
        if (!checked) {
            const v = wrap.querySelector('select[name="voltage"]');
            const l = document.getElementById('has_led_edit_' + pid);
            if (v) v.value = '';
            if (l) { l.checked = false; window.toggleLEDFieldEdit(pid, false); }
        }
    };

    window.toggleLEDFieldEdit = function (pid, checked) {
        const wrap = document.getElementById('ledFieldsEdit' + pid);
        if (!wrap) return;
        wrap.style.display = checked ? 'block' : 'none';
        if (!checked) {
            const t = wrap.querySelector('select[name="led_type"]');
            if (t) t.value = '';
        }
    };

})();