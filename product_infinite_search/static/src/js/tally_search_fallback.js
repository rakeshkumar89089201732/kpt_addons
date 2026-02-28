/** @odoo-module **/

/**
 * Tally-Style Product Search - Direct RPC Bypass
 * ================================================
 * For product.product and product.template, this completely overrides
 * loadOptionsSource to call our custom `tally_product_search` RPC method
 * instead of the standard `name_search`.
 *
 * This approach avoids ALL Python MRO conflicts with other modules
 * (like robust_search) that override name_search/name_search.
 *
 * We override loadOptionsSource (which is already async) instead of search()
 * to cleanly handle the .abort() mechanism without breaking promise chains.
 */

import { _t } from "@web/core/l10n/translation";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

const PRODUCT_MODELS = ["product.product", "product.template"];

// Store the original loadOptionsSource
const _originalLoadOptionsSource = Many2XAutocomplete.prototype.loadOptionsSource;

Many2XAutocomplete.prototype.loadOptionsSource = async function (request) {
    // For non-product models, use the standard flow (unchanged)
    if (!PRODUCT_MODELS.includes(this.props.resModel)) {
        return _originalLoadOptionsSource.call(this, request);
    }

    // ========= PRODUCT MODELS: Use tally_product_search directly =========

    // Safely abort previous request (if it has .abort)
    if (this.lastProm && typeof this.lastProm.abort === "function") {
        this.lastProm.abort(false);
    }

    // Call our custom RPC method that bypasses name_search entirely
    this.lastProm = this.orm.call(
        this.props.resModel,
        "tally_product_search",
        [],
        {
            search_term: request || "",
            domain: this.props.getDomain(),
            limit: this.props.searchLimit + 1,
        }
    );

    const records = await this.lastProm;

    // Build options from results (same structure as original loadOptionsSource)
    const options = records.map((result) => this.mapRecordToOption(result));

    // Quick Create option
    if (this.props.quickCreate && request.length) {
        options.push({
            label: _t('Create "%s"', request),
            classList: "o_m2o_dropdown_option o_m2o_dropdown_option_create",
            action: async (params) => {
                try {
                    await this.props.quickCreate(request, params);
                } catch (e) {
                    if (
                        e &&
                        e.exceptionName === "odoo.exceptions.ValidationError"
                    ) {
                        const context = this.getCreationContext(request);
                        return this.openMany2X({ context });
                    }
                    throw e;
                }
            },
        });
    }

    // Search More option
    if (!this.props.noSearchMore && records.length > 0) {
        options.push({
            label: _t("Search More..."),
            action: this.onSearchMore.bind(this, request),
            classList:
                "o_m2o_dropdown_option o_m2o_dropdown_option_search_more",
        });
    }

    // Start typing hint (when field is empty and no input yet)
    const canCreateEdit =
        "createEdit" in this.activeActions
            ? this.activeActions.createEdit
            : this.activeActions.create;
    if (
        !request.length &&
        !this.props.value &&
        (this.props.quickCreate || canCreateEdit)
    ) {
        options.push({
            label: _t("Start typing..."),
            classList: "o_m2o_start_typing",
            unselectable: true,
        });
    }

    // Create and edit option
    if (request.length && canCreateEdit) {
        const context = this.getCreationContext(request);
        options.push({
            label: _t("Create and edit..."),
            classList:
                "o_m2o_dropdown_option o_m2o_dropdown_option_create_edit",
            action: () => this.openMany2X({ context }),
        });
    }

    // No records message
    if (
        !records.length &&
        !this.activeActions.createEdit &&
        !this.props.quickCreate
    ) {
        options.push({
            label: _t("No records"),
            classList: "o_m2o_no_result",
            unselectable: true,
        });
    }

    return options;
};
