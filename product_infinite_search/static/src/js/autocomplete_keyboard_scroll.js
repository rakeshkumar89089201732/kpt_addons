/** @odoo-module **/

import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { patch } from "@web/core/utils/patch";

/**
 * Patch AutoComplete to auto-scroll dropdown when navigating with arrow keys
 * This ensures the selected item is always visible in the dropdown
 */
patch(AutoComplete.prototype, {
    /**
     * Override navigate method to add scrollIntoView behavior
     */
    navigate(direction) {
        // Call the original navigate method
        super.navigate(direction);
        
        // After navigation, scroll the active item into view
        this._scrollActiveItemIntoView();
    },

    /**
     * Scroll the currently active/selected item into view
     */
    _scrollActiveItemIntoView() {
        // Use setTimeout to ensure DOM is updated after state change
        setTimeout(() => {
            if (!this.root?.el || !this.state.activeSourceOption) {
                return;
            }

            // Get the active option ID
            const activeId = this.activeSourceOptionId;
            if (!activeId) {
                return;
            }

            // Find the active item in the dropdown by its ID
            const activeItem = this.root.el.querySelector(`#${activeId}`);
            
            if (activeItem) {
                // Get the dropdown container (the scrollable parent)
                const dropdownMenu = activeItem.closest('.dropdown-menu, .ui-autocomplete');
                
                if (dropdownMenu) {
                    // Calculate if the item is visible in the dropdown
                    const itemRect = activeItem.getBoundingClientRect();
                    const containerRect = dropdownMenu.getBoundingClientRect();
                    
                    const isAboveView = itemRect.top < containerRect.top;
                    const isBelowView = itemRect.bottom > containerRect.bottom;
                    
                    // Only scroll if the item is not fully visible
                    if (isAboveView || isBelowView) {
                        activeItem.scrollIntoView({
                            behavior: 'auto', // Use 'auto' instead of 'smooth' for instant response
                            block: 'nearest',
                            inline: 'nearest'
                        });
                    }
                }
            }
        }, 0);
    }
});
