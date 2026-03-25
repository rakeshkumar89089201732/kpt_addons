/** @odoo-module **/

/**
 * TEST FILE - Verify Create/Edit options are preserved
 * 
 * This file can be temporarily added to assets to test that:
 * 1. "Create and edit..." option appears when typing
 * 2. Quick create works (if enabled)
 * 3. Search More works
 * 4. Dropdown doesn't go off-screen
 * 
 * To test: Add this file to __manifest__.py assets, restart Odoo,
 * open browser console and check for test logs when using product fields.
 */

import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

const _originalLoadOptionsSource = Many2XAutocomplete.prototype.loadOptionsSource;

Many2XAutocomplete.prototype.loadOptionsSource = async function (request) {
    const result = await _originalLoadOptionsSource.call(this, request);
    
    // Log the options to verify Create/Edit options are present
    console.log('[Product Search Test] Options generated:', {
        request,
        optionsCount: result.length,
        hasCreateEdit: result.some(opt => opt.label?.includes('Create and edit')),
        hasQuickCreate: result.some(opt => opt.label?.includes('Create "')),
        hasSearchMore: result.some(opt => opt.label?.includes('Search More')),
        options: result.map(opt => opt.label),
    });
    
    return result;
};
