/** @odoo-module **/

/**
 * Voice search helper for product Many2One fields (sale/purchase/transfer lines).
 * Adds a mic button on focus for fields named product_id/product_tmpl_id.
 * Uses browser SpeechRecognition; falls back to manual typing if unsupported.
 */

const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;

function getFieldName(input) {
    const wrapper = input.closest('[data-field-name]');
    if (wrapper && wrapper.dataset.fieldName) {
        return wrapper.dataset.fieldName;
    }
    if (input.name) {
        return input.name.replace(/[^A-Za-z0-9_]/g, '');
    }
    const widget = input.closest('.o_field_widget');
    if (widget && widget.dataset && widget.dataset.name) {
        return widget.dataset.name;
    }
    return null;
}

function attachMicButton(input) {
    if (!SpeechRec) {
        return;
    }
    const fieldName = getFieldName(input);
    if (fieldName !== 'product_id' && fieldName !== 'product_tmpl_id') {
        return;
    }

    // Avoid duplicates
    if (input.parentElement.querySelector('.o_voice_m2o_btn')) {
        return;
    }

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'o_voice_m2o_btn btn btn-light btn-sm';
    btn.innerHTML = '<i class="fa fa-microphone"></i>';

    btn.addEventListener('click', (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        startListening(input);
    });

    const container = input.parentElement;
    if (!container) {
        return;
    }
    if (getComputedStyle(container).position === 'static') {
        container.style.position = 'relative';
    }
    container.appendChild(btn);
}

function startListening(input) {
    const recog = new SpeechRec();
    recog.lang = 'en-US';
    recog.continuous = false;
    recog.interimResults = false;

    recog.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInputValue(input, transcript);
    };
    try {
        recog.start();
    } catch (e) {
        // start may throw if invoked too quickly after a previous stop; ignore.
    }
}

function setInputValue(input, text) {
    if (!input) return;
    input.value = text;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', bubbles: true }));
}

// Global focus handler to attach mic to product many2one inputs
if (typeof document !== 'undefined') {
    document.addEventListener('focusin', (ev) => {
        const target = ev.target;
        if (!(target instanceof HTMLInputElement)) {
            return;
        }
        if (!target.classList.contains('o_input')) {
            return;
        }
        attachMicButton(target);
    });
}
