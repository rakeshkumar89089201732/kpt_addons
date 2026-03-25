# Product Infinite Search - UI Fixes Applied

## Issues Fixed

### 1. Keyboard Navigation Auto-Scroll
**Problem:** When using arrow keys (↑/↓) to navigate through the dropdown results, the selected item would go out of view but the dropdown wouldn't scroll automatically. Users had to manually scroll with the mouse to see the selected item.

**Fix:** Added `autocomplete_keyboard_scroll.js` that patches the AutoComplete component's `navigate()` method to automatically scroll the active item into view. The fix:
- Detects when navigation moves the active item outside the visible area
- Uses `scrollIntoView()` with `block: 'nearest'` to minimize unnecessary scrolling
- Only scrolls when the item is actually out of view (above or below)
- Uses `behavior: 'auto'` for instant response without animation lag

### 2. Dropdown Loading Off-Screen
**Problem:** Dropdown was forced to `position: "right-start"` which pushed it outside viewport on smaller screens or when field is near the right edge.

**Fix:** Removed the forced positioning in `autocomplete_dropdown_sidebar.js`. Now uses Odoo's default positioning logic (bottom-start with auto-flip) which automatically adjusts based on available space.

### 2. Missing Create/Edit Options
**Problem:** "Create and edit..." and quick create options were not showing in the dropdown due to improper `activeActions` checking.

**Fix:** Updated `tally_search_fallback.js` to properly check `activeActions` using optional chaining (`?.`) and fixed the logic to always show create/edit options when the field allows creation.

### 3. Dropdown Dimensions Not Responsive
**Problem:** Fixed min/max dimensions (460px-580px width, 400px-650px height) caused off-screen rendering on smaller screens.

**Fix:** Updated `product_search_dropdown.scss` to use responsive dimensions:
- `max-width: min(580px, 90vw)` - adapts to viewport width
- `max-height: min(650px, 80vh)` - adapts to viewport height
- `min-height: 200px` - reduced from 400px to prevent off-screen
- Added `overflow-x: hidden` to prevent horizontal scrolling

### 4. Backend Data Format Mismatch
**Problem:** The `tally_product_search` backend method returns `[[id, display_name], ...]` tuples, but the JS code was trying to use `mapRecordToOption()` which expects objects.

**Fix:** Updated the record mapping to properly destructure the tuple format:
```javascript
const options = records.map(([id, display_name]) => ({
    value: id,
    label: display_name,
}));
```

## Files Modified

1. `static/src/js/autocomplete_keyboard_scroll.js` - **NEW** - Auto-scroll on keyboard navigation
2. `static/src/js/autocomplete_dropdown_sidebar.js` - Removed forced positioning
3. `static/src/js/tally_search_fallback.js` - Fixed create/edit options and record mapping
4. `static/src/scss/product_search_dropdown.scss` - Made dimensions responsive
5. `__manifest__.py` - Added autocomplete_keyboard_scroll.js to assets

## Testing Checklist

### Test 1: Keyboard Navigation Auto-Scroll
- [ ] Open a Sales Order / Purchase Order / Quotation
- [ ] Click on the Product field in an order line
- [ ] Type to search and get many results (e.g., "KPT")
- [ ] Use ↓ (down arrow) key repeatedly to navigate through results
- [ ] Verify the dropdown automatically scrolls to keep the selected item visible
- [ ] Use ↑ (up arrow) key to navigate backwards
- [ ] Verify scrolling works in both directions
- [ ] Verify no unnecessary scrolling when item is already visible

### Test 2: Dropdown Positioning
- [ ] Open a Sales Order / Purchase Order / Quotation
- [ ] Click on the Product field in an order line
- [ ] Verify dropdown appears within viewport (not cut off)
- [ ] Try with field near right edge of screen
- [ ] Try on different screen sizes

### Test 2: Create/Edit Options
- [ ] Click on Product field and type a search term (e.g., "test product xyz")
- [ ] Verify "Create and edit..." option appears at the bottom
- [ ] Click "Create and edit..." and verify product creation form opens
- [ ] Create a product and verify it's properly saved

### Test 3: Quick Create (if enabled)
- [ ] Type a product name that doesn't exist
- [ ] Verify 'Create "product name"' option appears
- [ ] Click it and verify quick create works

### Test 4: Search Functionality
- [ ] Type partial product names and verify Tally-style search works
- [ ] Verify "Search More..." option appears
- [ ] Verify search results show correctly

### Test 5: Pricelist Upload
- [ ] Go to Sales > Products > Pricelists
- [ ] Create or edit a pricelist
- [ ] Add pricelist items with product selection
- [ ] Verify product search works in pricelist items
- [ ] Import/upload pricelist data and verify products are selectable

### Test 6: Product Variants
- [ ] Go to Sales > Products > Products
- [ ] Create a product with variants (attributes)
- [ ] Verify variant selection works in order lines
- [ ] Verify search works for both templates and variants

## Upgrade Instructions

1. **Update the module:**
   ```bash
   python odoo-bin -c odoo.conf -d YOUR_DATABASE -u product_infinite_search --stop-after-init
   ```

2. **Clear browser cache:**
   - Press Ctrl+Shift+R (or Cmd+Shift+R on Mac) to hard refresh
   - Or clear browser cache completely

3. **Test in different scenarios:**
   - Sales Orders
   - Purchase Orders
   - Quotations
   - Pricelists
   - Product Variants
   - Different screen sizes

## Rollback (if needed)

If issues occur, you can temporarily disable the module:
```bash
python odoo-bin -c odoo.conf -d YOUR_DATABASE -i product_infinite_search --stop-after-init
```

Then investigate logs and re-enable after fixing.

## Notes

- The Tally-style search functionality remains unchanged
- All backend search methods (`tally_product_search`, `name_search`, `_name_search`) are preserved
- The fixes only affect UI positioning and option display
- No database changes required
