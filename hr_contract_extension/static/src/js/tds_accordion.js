/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class TDSAccordionWidget extends Component {
    setup() {
        this.state = useState({
            sections: {
                employee: true,
                income: true,
                other_income: false,
                hra: false,
                deductions: false,
                tax: true,
                monthly: false,
            }
        });

        onMounted(() => {
            this.initializeAccordion();
        });
    }

    initializeAccordion() {
        const headers = document.querySelectorAll('.tds_accordion_header');
        headers.forEach(header => {
            header.addEventListener('click', (e) => {
                const section = header.closest('.tds_accordion_section');
                const sectionId = section.dataset.section;
                
                if (section.classList.contains('collapsed')) {
                    section.classList.remove('collapsed');
                    this.state.sections[sectionId] = true;
                } else {
                    section.classList.add('collapsed');
                    this.state.sections[sectionId] = false;
                }
            });
        });
    }

    toggleSection(sectionId) {
        this.state.sections[sectionId] = !this.state.sections[sectionId];
    }
}

TDSAccordionWidget.template = "hr_contract_extension.TDSAccordionWidget";

// Register as a field widget if needed
registry.category("fields").add("tds_accordion", TDSAccordionWidget);

// Simple vanilla JS initialization for non-OWL contexts
document.addEventListener('DOMContentLoaded', function() {
    initTDSAccordion();
});

function initTDSAccordion() {
    const headers = document.querySelectorAll('.tds_accordion_header');
    
    headers.forEach(header => {
        header.addEventListener('click', function(e) {
            e.preventDefault();
            const section = this.closest('.tds_accordion_section');
            
            // Toggle collapsed state
            section.classList.toggle('collapsed');
            
            // Optional: Close other sections (accordion behavior)
            // Uncomment below if you want only one section open at a time
            /*
            const allSections = document.querySelectorAll('.tds_accordion_section');
            allSections.forEach(s => {
                if (s !== section) {
                    s.classList.add('collapsed');
                }
            });
            */
        });
    });
    
    // Initialize: collapse all except first two sections
    const sections = document.querySelectorAll('.tds_accordion_section');
    sections.forEach((section, index) => {
        if (index > 1) {
            section.classList.add('collapsed');
        }
    });
}

// Export for module use
export function setupTDSAccordion() {
    initTDSAccordion();
}
