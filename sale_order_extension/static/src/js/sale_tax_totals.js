/** @odoo-module **/

import { TaxTotalsComponent } from "@account/components/tax_totals/tax_totals";
import { parseFloat } from "@web/views/fields/parsers";
import { formatFloat } from "@web/core/utils/numbers";
import { registry } from "@web/core/registry";
import { useRef, useState, onPatched } from "@odoo/owl";

export class KptSaleTaxTotalsComponent extends TaxTotalsComponent {
    setup() {
        super.setup();
        this.roundingInput = useRef("roundingValueInput");
        this.roundingState = useState({ value: "readonly" });
        onPatched(() => {
            if (this.roundingState.value === "edit" && this.roundingInput.el) {
                const newVal = formatFloat(this.props.record.data.round_off_amount || 0, {
                    digits: this.currency && this.currency.digits,
                });
                this.roundingInput.el.value = newVal;
                this.roundingInput.el.focus();
            }
        });
    }

    setRoundingState(value) {
        if (["readonly", "edit", "disable"].includes(value)) {
            this.roundingState.value = value;
        } else {
            this.roundingState.value = "readonly";
        }
    }

    async onChangeRoundingValue() {
        this.setRoundingState("disable");
        const oldValue = this.props.record.data.round_off_amount || 0;
        let newValue;
        try {
            newValue = parseFloat(this.roundingInput.el.value);
        } catch {
            this.setRoundingState("edit");
            return;
        }
        await this.props.record.update({ round_off_amount: newValue });
        this.setRoundingState("readonly");
    }
}

KptSaleTaxTotalsComponent.template = "sale_order_extension.KptSaleTaxTotalsField";

registry.category("fields").add("kpt-sale-tax-totals-field", {
    component: KptSaleTaxTotalsComponent,
});
