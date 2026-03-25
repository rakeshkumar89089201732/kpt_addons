/** @odoo-module **/

import { ListRenderer } from "@web/views/list/list_renderer";
import { patch } from "@web/core/utils/patch";

/**
 * Enhanced list renderer for Monthly Attendance Wizard
 * Improves visual hierarchy and user experience with Year -> Month -> Employee grouping
 */
patch(ListRenderer.prototype, {
    setup() {
        super.setup();
        if (this.props.resModel === 'monthly.attendance.set.wizard') {
            this.setupMonthlyAttendanceEnhancements();
        }
    },
    
    setupMonthlyAttendanceEnhancements() {
        // Use MutationObserver to watch for DOM changes
        this.enhanceGroupHeaders();
        
        // Re-enhance after render
        this.on("RENDERED", this, () => {
            setTimeout(() => this.enhanceGroupHeaders(), 50);
        });
    },
    
    enhanceGroupHeaders() {
        if (!this.el) return;
        
        // Format year headers (Level 0)
        const yearHeaders = this.el.querySelectorAll('.o_group_header_row_level_0');
        yearHeaders.forEach(header => {
            const groupName = header.querySelector('.o_group_name');
            if (groupName && !groupName.dataset.enhanced) {
                const text = groupName.textContent.trim();
                // Extract year and count - format: "2026 (1)" or "2026"
                const match = text.match(/(\d{4})(?:\s*\((\d+)\))?/);
                if (match) {
                    const [, year, count] = match;
                    const countText = count ? ` (${count} ${count === '1' ? 'record' : 'records'})` : '';
                    groupName.innerHTML = `
                        <span style="display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 1.3em; filter: drop-shadow(0 1px 2px rgba(0,0,0,0.2));">📅</span>
                            <span style="font-weight: 700; text-transform: uppercase; letter-spacing: 1px;">Year ${year}</span>
                            <span style="opacity: 0.9; font-size: 0.9em; background: rgba(255,255,255,0.25); padding: 2px 8px; border-radius: 12px;">${countText}</span>
                        </span>
                    `;
                    groupName.dataset.enhanced = 'true';
                }
            }
        });
        
        // Format month headers (Level 1)
        const monthHeaders = this.el.querySelectorAll('.o_group_header_row_level_1');
        monthHeaders.forEach(header => {
            const groupName = header.querySelector('.o_group_name');
            if (groupName && !groupName.dataset.enhanced) {
                const text = groupName.textContent.trim();
                // Extract month name and count - format: "February (1)" or "02 (1)"
                const match = text.match(/(\w+|\d{2})(?:\s*\((\d+)\))?/);
                if (match) {
                    const [, month, count] = match;
                    // Convert numeric month to name if needed
                    const monthNames = {
                        '01': 'January', '02': 'February', '03': 'March',
                        '04': 'April', '05': 'May', '06': 'June',
                        '07': 'July', '08': 'August', '09': 'September',
                        '10': 'October', '11': 'November', '12': 'December'
                    };
                    const monthDisplay = monthNames[month] || month;
                    const countText = count ? ` (${count} ${count === '1' ? 'employee' : 'employees'})` : '';
                    groupName.innerHTML = `
                        <span style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-size: 1.2em; filter: drop-shadow(0 1px 2px rgba(0,0,0,0.2));">📆</span>
                            <span style="font-weight: 600;">${monthDisplay}</span>
                            <span style="opacity: 0.9; font-size: 0.85em; background: rgba(255,255,255,0.25); padding: 2px 8px; border-radius: 12px;">${countText}</span>
                        </span>
                    `;
                    groupName.dataset.enhanced = 'true';
                }
            }
        });
        
        // Enhance employee rows with better visual indicators
        const employeeRows = this.el.querySelectorAll('.o_data_row');
        employeeRows.forEach((row, index) => {
            if (!row.dataset.enhanced) {
                const employeeCell = row.querySelector('[data-name="employee_id"]');
                if (employeeCell) {
                    employeeCell.style.fontWeight = '500';
                    employeeCell.style.color = '#2c3e50';
                }
                row.dataset.enhanced = 'true';
            }
        });
    },
    
    onWillUpdate() {
        super.onWillUpdate?.();
        if (this.props.resModel === 'monthly.attendance.set.wizard') {
            // Clear enhanced flags to allow re-enhancement
            if (this.el) {
                const enhancedElements = this.el.querySelectorAll('[data-enhanced="true"]');
                enhancedElements.forEach(el => delete el.dataset.enhanced);
            }
            // Re-enhance after updates
            setTimeout(() => this.enhanceGroupHeaders(), 150);
        }
    },
    
    onWillPatch() {
        super.onWillPatch?.();
        if (this.props.resModel === 'monthly.attendance.set.wizard') {
            // Clear enhanced flags before patch
            if (this.el) {
                const enhancedElements = this.el.querySelectorAll('[data-enhanced="true"]');
                enhancedElements.forEach(el => delete el.dataset.enhanced);
            }
        }
    },
});
