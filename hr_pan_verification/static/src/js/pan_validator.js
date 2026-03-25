/** @odoo-module **/

import { registry } from "@web/core/registry";
import { CharField } from "@web/views/fields/char/char_field";
import { useInputField } from "@web/views/fields/input_field_hook";
import { Component, useState, onWillUpdateProps } from "@odoo/owl";

/**
 * PAN Validation Logic (Client-side)
 * 
 * PAN Structure: AAAAA9999A
 * - First 3 characters: Alphabetic series (AAA to ZZZ)
 * - 4th character: Type of holder
 *   P = Individual, C = Company, H = HUF, F = Firm, A = AOP, T = Trust, etc.
 * - 5th character: First letter of PAN holder's name/surname
 * - Next 4 characters: Sequential number (0001 to 9999)
 * - Last character: Alphabetic check digit
 */

export class PANValidator {
    /**
     * Validate PAN format and structure
     * @param {string} pan - PAN number to validate
     * @returns {Object} - {valid: boolean, message: string, type: string}
     */
    static validate(pan) {
        if (!pan) {
            return {
                valid: false,
                message: 'PAN number is required',
                type: 'error',
                status: 'not_verified'
            };
        }

        // Normalize: uppercase and trim
        pan = pan.trim().toUpperCase();

        // Check length
        if (pan.length !== 10) {
            return {
                valid: false,
                message: 'PAN must be exactly 10 characters',
                type: 'error',
                status: 'not_verified'
            };
        }

        // Check format: AAAAA9999A
        const panPattern = /^[A-Z]{5}[0-9]{4}[A-Z]$/;
        if (!panPattern.test(pan)) {
            return {
                valid: false,
                message: 'Invalid PAN format. Expected: ABCDE1234F (5 letters, 4 digits, 1 letter)',
                type: 'error',
                status: 'not_verified'
            };
        }

        // Validate 4th character (holder type)
        const holderType = pan.charAt(3);
        const validHolderTypes = {
            'P': 'Individual',
            'C': 'Company',
            'H': 'Hindu Undivided Family (HUF)',
            'F': 'Firm/Partnership',
            'A': 'Association of Persons (AOP)',
            'T': 'Trust',
            'B': 'Body of Individuals (BOI)',
            'L': 'Local Authority',
            'J': 'Artificial Juridical Person',
            'G': 'Government',
        };

        if (!validHolderTypes[holderType]) {
            return {
                valid: false,
                message: `Invalid holder type '${holderType}' in 4th position. Must be one of: P, C, H, F, A, T, B, L, J, G`,
                type: 'warning',
                status: 'failed'
            };
        }

        // Validate first 3 characters (series)
        const series = pan.substring(0, 3);
        if (!/^[A-Z]{3}$/.test(series)) {
            return {
                valid: false,
                message: 'First 3 characters must be alphabets (AAA-ZZZ)',
                type: 'error',
                status: 'failed'
            };
        }

        // Validate 5th character (first letter of name)
        const nameInitial = pan.charAt(4);
        if (!/^[A-Z]$/.test(nameInitial)) {
            return {
                valid: false,
                message: '5th character must be an alphabet (first letter of name)',
                type: 'error',
                status: 'failed'
            };
        }

        // Validate sequential number (6th to 9th characters)
        const seqNumber = pan.substring(5, 9);
        if (!/^[0-9]{4}$/.test(seqNumber)) {
            return {
                valid: false,
                message: 'Characters 6-9 must be digits (0001-9999)',
                type: 'error',
                status: 'failed'
            };
        }

        // Check if sequential number is valid (not 0000)
        if (seqNumber === '0000') {
            return {
                valid: false,
                message: 'Sequential number cannot be 0000',
                type: 'error',
                status: 'failed'
            };
        }

        // All validations passed
        return {
            valid: true,
            message: `Valid PAN for ${validHolderTypes[holderType]}`,
            type: 'success',
            status: 'verified',
            holderType: validHolderTypes[holderType],
            pan: pan
        };
    }

    /**
     * Extract information from PAN
     * @param {string} pan - Valid PAN number
     * @returns {Object} - Extracted information
     */
    static extractInfo(pan) {
        if (!pan || pan.length !== 10) {
            return null;
        }

        pan = pan.trim().toUpperCase();

        const holderTypes = {
            'P': 'Individual',
            'C': 'Company',
            'H': 'Hindu Undivided Family (HUF)',
            'F': 'Firm/Partnership',
            'A': 'Association of Persons (AOP)',
            'T': 'Trust',
            'B': 'Body of Individuals (BOI)',
            'L': 'Local Authority',
            'J': 'Artificial Juridical Person',
            'G': 'Government',
        };

        return {
            series: pan.substring(0, 3),
            holderType: holderTypes[pan.charAt(3)] || 'Unknown',
            holderTypeCode: pan.charAt(3),
            nameInitial: pan.charAt(4),
            sequentialNumber: pan.substring(5, 9),
            checkDigit: pan.charAt(9),
            isIndividual: pan.charAt(3) === 'P',
            isCompany: pan.charAt(3) === 'C',
        };
    }
}

/**
 * Custom PAN Field Widget with real-time validation
 */
export class PANField extends CharField {
    setup() {
        super.setup();
        this.state = useState({
            validationResult: null,
            showValidation: false,
        });

        // Validate on input
        useInputField({
            getValue: () => this.props.value || "",
            refName: "input",
            parse: (v) => this.parse(v),
        });
    }

    get validationClass() {
        if (!this.state.validationResult) return '';
        
        switch (this.state.validationResult.status) {
            case 'verified':
                return 'text-success';
            case 'failed':
                return 'text-danger';
            default:
                return 'text-muted';
        }
    }

    get validationIcon() {
        if (!this.state.validationResult) return '';
        
        switch (this.state.validationResult.status) {
            case 'verified':
                return 'fa-check-circle';
            case 'failed':
                return 'fa-times-circle';
            default:
                return 'fa-question-circle';
        }
    }

    onInput(ev) {
        const value = ev.target.value;
        if (value) {
            // Normalize to uppercase
            const normalized = value.trim().toUpperCase();
            ev.target.value = normalized;
            
            // Validate
            const result = PANValidator.validate(normalized);
            this.state.validationResult = result;
            this.state.showValidation = true;

            // Update the field value
            this.props.update(normalized);
        } else {
            this.state.validationResult = null;
            this.state.showValidation = false;
            this.props.update(value);
        }
    }

    onBlur(ev) {
        super.onBlur?.(ev);
        // Keep validation visible after blur
        if (this.state.validationResult) {
            this.state.showValidation = true;
        }
    }
}

PANField.template = "hr_pan_verification.PANField";
PANField.supportedTypes = ["char"];

registry.category("fields").add("pan_field", PANField);
