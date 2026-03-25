/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";

export class ShortcutRecorder extends Component {
    setup() {
        this.state = useState({
            recording: false,
            recordedKey: '',
            ctrl: false,
            alt: false,
            shift: false,
            meta: false,
        });
    }
    
    startRecording() {
        this.state.recording = true;
        this.state.recordedKey = '';
        this.state.ctrl = false;
        this.state.alt = false;
        this.state.shift = false;
        this.state.meta = false;
    }
    
    stopRecording() {
        this.state.recording = false;
    }
    
    onKeyDown(event) {
        if (!this.state.recording) return;
        
        event.preventDefault();
        event.stopPropagation();
        
        this.state.ctrl = event.ctrlKey;
        this.state.alt = event.altKey;
        this.state.shift = event.shiftKey;
        this.state.meta = event.metaKey;
        
        if (!['Control', 'Alt', 'Shift', 'Meta'].includes(event.key)) {
            this.state.recordedKey = event.key;
            this.stopRecording();
            
            if (this.props.onRecorded) {
                this.props.onRecorded({
                    key_code: event.key,
                    ctrl_key: this.state.ctrl,
                    alt_key: this.state.alt,
                    shift_key: this.state.shift,
                    meta_key: this.state.meta,
                });
            }
        }
    }
    
    getDisplayText() {
        if (!this.state.recording && !this.state.recordedKey) {
            return 'Click to record';
        }
        
        if (this.state.recording) {
            const parts = [];
            if (this.state.ctrl) parts.push('Ctrl');
            if (this.state.alt) parts.push('Alt');
            if (this.state.shift) parts.push('Shift');
            if (this.state.meta) parts.push('Meta');
            
            if (parts.length === 0) {
                return 'Press a key...';
            }
            return parts.join(' + ') + ' + ...';
        }
        
        const parts = [];
        if (this.state.ctrl) parts.push('Ctrl');
        if (this.state.alt) parts.push('Alt');
        if (this.state.shift) parts.push('Shift');
        if (this.state.meta) parts.push('Meta');
        if (this.state.recordedKey) parts.push(this.state.recordedKey);
        
        return parts.join(' + ');
    }
}

ShortcutRecorder.template = "keyboard_shortcuts_config.ShortcutRecorder";
ShortcutRecorder.props = {
    onRecorded: { type: Function, optional: true },
};

registry.category("fields").add("shortcut_recorder", ShortcutRecorder);
