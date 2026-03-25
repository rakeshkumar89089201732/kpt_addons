/** @odoo-module */

import { Component, onWillStart, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { formatCurrency } from "@web/core/currency";

export class SelectedItemsDialog extends Component {
    static template = "odoo_product_catalog_selected_items.SelectedItemsDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        orderId: Number,
        resModel: String,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            lines: [],
            loading: true,
            total: 0,
            currencyId: null,
        });

        onWillStart(async () => {
            await this.loadSelectedItems();
        });
    }

    async loadSelectedItems() {
        try {
            // Determine line model and fields based on order model
            let lineModel = '';
            let lineField = '';
            let qtyField = '';

            if (this.props.resModel === 'sale.order') {
                lineModel = 'sale.order.line';
                lineField = 'order_line';
                qtyField = 'product_uom_qty';
            } else if (this.props.resModel === 'purchase.order') {
                lineModel = 'purchase.order.line';
                lineField = 'order_line';
                qtyField = 'product_qty';
            } else {
                // Fallback or generic handling? 
                // Try to guess default One2many field 'order_line'
                lineModel = this.props.resModel + '.line';
                lineField = 'order_line';
                qtyField = 'product_qty';
            }

            // 1. Fetch order to get currency and line IDs
            const orderr = await this.orm.read(this.props.resModel, [this.props.orderId], [lineField, 'currency_id']);
            if (!orderr || !orderr.length) return;

            const lineIds = orderr[0][lineField];
            this.state.currencyId = orderr[0].currency_id[0];

            if (!lineIds || !lineIds.length) {
                this.state.loading = false;
                return;
            }

            // 2. Fetch line details
            const lines = await this.orm.read(lineModel, lineIds, ['product_id', qtyField, 'price_unit', 'price_subtotal']);

            // Filter out section/note lines (where product_id is false)
            this.state.lines = lines.filter(l => l.product_id).map(l => ({
                id: l.id,
                product_name: l.product_id[1],
                quantity: l[qtyField],
                price: l.price_unit,
                subtotal: l.price_subtotal,
            }));

            // Calculate total
            this.state.total = this.state.lines.reduce((acc, l) => acc + l.subtotal, 0);

        } catch (error) {
            console.error("Error loading selected items:", error);
        } finally {
            this.state.loading = false;
        }
    }

    formatMoney(amount) {
        // Simple formatting, ideally use currency service if needed but for quick view generic is ok
        return amount.toFixed(2);
    }
}
