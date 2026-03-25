/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";

/**
 * Template Variables for Offer Letter HTML editor fields.
 *
 * These are registered as powerbox commands so users can type "/" in any
 * Html field on the offer letter form and pick a variable from the list.
 *
 * Changes from original:
 * - Added [OFFER_VALID_TILL] placeholder for the new offer validity date field.
 * - Grouped variables under two categories for easier discovery.
 */
const TEMPLATE_VARIABLES = [
    // ─── Candidate Variables ───────────────────────────────────────────────────
    { value: '[CANDIDATE_NAME]', label: '[CANDIDATE_NAME]', description: _lt("Candidate's full name"), category: 'Offer - Candidate' },
    { value: '[EMAIL]',          label: '[EMAIL]',          description: _lt("Candidate's email address"), category: 'Offer - Candidate' },
    { value: '[PHONE]',          label: '[PHONE]',          description: _lt("Candidate's phone number"), category: 'Offer - Candidate' },

    // ─── Job / Offer Variables ─────────────────────────────────────────────────
    { value: '[POSITION]',        label: '[POSITION]',        description: _lt('Job position name'), category: 'Offer - Job' },
    { value: '[DEPARTMENT]',      label: '[DEPARTMENT]',      description: _lt('Department name'), category: 'Offer - Job' },
    { value: '[WORK_LOCATION]',   label: '[WORK_LOCATION]',   description: _lt('Work location'), category: 'Offer - Job' },
    { value: '[WORK_HOURS]',      label: '[WORK_HOURS]',      description: _lt('Working hours'), category: 'Offer - Job' },
    { value: '[OFFER_DATE]',      label: '[OFFER_DATE]',      description: _lt('Formatted offer date'), category: 'Offer - Job' },
    { value: '[JOINING_DATE]',    label: '[JOINING_DATE]',    description: _lt('Formatted joining date'), category: 'Offer - Job' },
    { value: '[OFFER_VALID_TILL]', label: '[OFFER_VALID_TILL]', description: _lt('Offer valid till date'), category: 'Offer - Job' },
    { value: '[PROBATION_PERIOD]', label: '[PROBATION_PERIOD]', description: _lt('Probation period (months)'), category: 'Offer - Job' },
    { value: '[NOTICE_PERIOD]',   label: '[NOTICE_PERIOD]',   description: _lt('Notice period (days)'), category: 'Offer - Job' },

    // ─── Salary Variables ──────────────────────────────────────────────────────
    { value: '[BASIC_SALARY]',  label: '[BASIC_SALARY]',  description: _lt('Basic salary amount'), category: 'Offer - Salary' },
    { value: '[GROSS_SALARY]',  label: '[GROSS_SALARY]',  description: _lt('Gross monthly salary'), category: 'Offer - Salary' },
    { value: '[CTC_ANNUAL]',    label: '[CTC_ANNUAL]',    description: _lt('Annual CTC'), category: 'Offer - Salary' },

    // ─── Company Variables ─────────────────────────────────────────────────────
    { value: '[COMPANY]',         label: '[COMPANY]',         description: _lt('Company name'), category: 'Offer - Company' },
    { value: '[COMPANY_ADDRESS]', label: '[COMPANY_ADDRESS]', description: _lt('Full formatted company address'), category: 'Offer - Company' },
    { value: '[COMPANY_PHONE]',   label: '[COMPANY_PHONE]',   description: _lt('Company phone'), category: 'Offer - Company' },
    { value: '[COMPANY_EMAIL]',   label: '[COMPANY_EMAIL]',   description: _lt('Company email'), category: 'Offer - Company' },
    { value: '[RESPONSIBLE_NAME]', label: '[RESPONSIBLE_NAME]', description: _lt('Responsible person name'), category: 'Offer - Company' },
];

// Register all variables as powerbox commands in the HTML editor
const powerboxRegistry = registry.category("powerbox");

TEMPLATE_VARIABLES.forEach((variable) => {
    powerboxRegistry.add(`template_var_${variable.value}`, {
        name: variable.label,
        // Keep this lazy: template strings would force translation too early.
        description: variable.description,
        category: variable.category,
        fontawesome: "fa-code",
        action(dispatch) {
            dispatch("INSERT_TEXT", { text: variable.value });
        },
    });
});
