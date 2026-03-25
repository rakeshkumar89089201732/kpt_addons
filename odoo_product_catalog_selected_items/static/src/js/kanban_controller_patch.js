/** @odoo-module */

import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { SelectedItemsDialog } from "./selected_items_dialog";
import { onWillStart, useState, useSubEnv, EventBus } from "@odoo/owl";

patch(ProductCatalogKanbanController.prototype, {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.state = useState({ selectedCount: 0 });
        this.productCatalogBus = new EventBus();

        useSubEnv({ productCatalogBus: this.productCatalogBus });

        onWillStart(async () => {
            await this.updateSelectedCount();
        });

        this.productCatalogBus.addEventListener('update_count', async () => {
            await this.updateSelectedCount();
        });
    },

    async updateSelectedCount() {
        try {
            let lineModel = '';
            if (this.orderResModel === 'sale.order') {
                lineModel = 'sale.order.line';
            } else if (this.orderResModel === 'purchase.order') {
                lineModel = 'purchase.order.line';
            } else {
                lineModel = this.orderResModel + '.line'; // Fallback
            }

            const count = await this.orm.searchCount(lineModel, [
                ['order_id', '=', this.orderId],
                ['product_id', '!=', false]
            ]);
            this.state.selectedCount = count;
        } catch (e) {
            console.error("Failed to update selected count", e);
        }
    },

    openSelectedItems() {
        this.dialog.add(SelectedItemsDialog, {
            orderId: this.orderId,
            resModel: this.orderResModel,
        });
    }
});
