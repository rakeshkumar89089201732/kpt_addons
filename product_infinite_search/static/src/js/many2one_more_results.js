/** @odoo-module **/

import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

// Dropdown limit: show many more products (was 7/8). "Search More..." uses searchMoreLimit.
const DROPDOWN_SEARCH_LIMIT = 80;
const SEARCH_MORE_LIMIT = 2000;

Many2XAutocomplete.defaultProps = {
    ...Many2XAutocomplete.defaultProps,
    searchLimit: DROPDOWN_SEARCH_LIMIT,
    searchMoreLimit: SEARCH_MORE_LIMIT,
};

// Ensure Many2One field always passes high limits to the autocomplete (e.g. Product on order lines).
const originalGetProps = Object.getOwnPropertyDescriptor(
    Many2OneField.prototype,
    "Many2XAutocompleteProps"
);
if (originalGetProps && originalGetProps.get) {
    const originalGet = originalGetProps.get;
    Object.defineProperty(Many2OneField.prototype, "Many2XAutocompleteProps", {
        get() {
            return {
                ...originalGet.call(this),
                searchLimit: DROPDOWN_SEARCH_LIMIT,
                searchMoreLimit: SEARCH_MORE_LIMIT,
            };
        },
        configurable: true,
        enumerable: true,
    });
}
