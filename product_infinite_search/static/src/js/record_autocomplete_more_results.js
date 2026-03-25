/** @odoo-module **/

import { RecordAutocomplete } from "@web/core/record_selectors/record_autocomplete";
import { _t } from "@web/core/l10n/translation";

// Show many more results in the dropdown (default was 8)
const DROPDOWN_SEARCH_LIMIT = 80;

const originalLoadOptionsSource = RecordAutocomplete.prototype.loadOptionsSource;
RecordAutocomplete.prototype.loadOptionsSource = async function (name) {
    if (this.lastProm) {
        this.lastProm.abort(false);
    }
    this.lastProm = this.search(name, DROPDOWN_SEARCH_LIMIT + 1);
    const nameGets = (await this.lastProm).map(([id, label]) => [
        id,
        label ? label.split("\n")[0] : _t("Unnamed"),
    ]);
    this.addNames(nameGets);
    const options = nameGets.map(([value, label]) => ({ value, label }));
    if (DROPDOWN_SEARCH_LIMIT < nameGets.length) {
        options.push({
            label: _t("Search More..."),
            action: this.onSearchMore.bind(this, name),
            classList: "o_m2o_dropdown_option",
        });
    }
    if (options.length === 0) {
        options.push({ label: _t("(no result)"), unselectable: true });
    }
    return options;
};
