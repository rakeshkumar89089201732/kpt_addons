/** @odoo-module **/

import { AutoComplete } from "@web/core/autocomplete/autocomplete";

// Show dropdown at the side of the input (right) instead of above/below
Object.defineProperty(AutoComplete.prototype, "dropdownOptions", {
    get() {
        return {
            position: "right-start",
            margin: 8,
        };
    },
    configurable: true,
    enumerable: true,
});
