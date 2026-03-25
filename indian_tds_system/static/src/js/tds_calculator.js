/** @odoo-module **/

import { registry } from "@web/core/registry";

// Placeholder for TDS Calculator logic
export const tdsCalculator = {
    calculate() {
        console.log("TDS calculation triggered");
    }
};

registry.category("actions").add("indian_tds_system.calculator", tdsCalculator);
