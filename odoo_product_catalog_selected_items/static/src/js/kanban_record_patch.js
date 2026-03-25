/** @odoo-module */

import { ProductCatalogKanbanRecord } from "@product/product_catalog/kanban_record";
import { patch } from "@web/core/utils/patch";

patch(ProductCatalogKanbanRecord.prototype, {
    async _updateQuantity() {
        await super._updateQuantity(...arguments);
        // Trigger update on the bus provided by the controller
        if (this.env.productCatalogBus) {
            this.env.productCatalogBus.trigger('update_count');
        }
    }
});
