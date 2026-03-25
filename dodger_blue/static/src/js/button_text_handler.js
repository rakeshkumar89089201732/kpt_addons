/** @odoo-module **/

import { Component, onMounted, onPatched } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

/**
 * Intelligently adds "Save" and "Discard" text to icon-only buttons
 * while avoiding duplication where text already exists.
 */
function addButtonTextIfNeeded() {
    // Find all Save buttons
    const saveButtons = document.querySelectorAll('.o_form_button_save');
    saveButtons.forEach(button => {
        // Check if button only contains an icon (no text nodes)
        const hasText = Array.from(button.childNodes).some(node =>
            node.nodeType === Node.TEXT_NODE && node.textContent.trim().length > 0
        );

        if (!hasText && !button.dataset.textAdded) {
            // Add text only if it doesn't exist
            const textNode = document.createTextNode(' Save');
            button.appendChild(textNode);
            button.dataset.textAdded = 'true';
        }
    });

    // Find all Discard/Cancel buttons
    const cancelButtons = document.querySelectorAll('.o_form_button_cancel');
    cancelButtons.forEach(button => {
        // Check if button only contains an icon (no text nodes)
        const hasText = Array.from(button.childNodes).some(node =>
            node.nodeType === Node.TEXT_NODE && node.textContent.trim().length > 0
        );

        if (!hasText && !button.dataset.textAdded) {
            // Add text only if it doesn't exist
            const textNode = document.createTextNode(' Discard');
            button.appendChild(textNode);
            button.dataset.textAdded = 'true';
        }
    });
}

// Patch FormController to add button text after rendering
patch(FormController.prototype, {
    setup() {
        super.setup();

        onMounted(() => {
            addButtonTextIfNeeded();
        });

        onPatched(() => {
            addButtonTextIfNeeded();
        });
    },
});

// Setup MutationObserver only when DOM is ready
function setupObserver() {
    if (document.body) {
        const observer = new MutationObserver(() => {
            addButtonTextIfNeeded();
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
}

// Run when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        addButtonTextIfNeeded();
        setupObserver();
    });
} else {
    addButtonTextIfNeeded();
    setupObserver();
}
