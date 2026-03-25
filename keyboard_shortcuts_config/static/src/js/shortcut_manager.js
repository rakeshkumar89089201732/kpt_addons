/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";

const { Component, onWillStart, onMounted, onWillUnmount } = owl;

class ShortcutManager extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        
        this.shortcuts = [];
        this.boundHandler = this.handleKeyPress.bind(this);
        
        onWillStart(async () => {
            await this.loadShortcuts();
        });
        
        onMounted(() => {
            document.addEventListener('keydown', this.boundHandler, true);
        });
        
        onWillUnmount(() => {
            document.removeEventListener('keydown', this.boundHandler, true);
        });
    }
    
    async loadShortcuts() {
        try {
            this.shortcuts = await this.orm.call(
                'keyboard.shortcut',
                'get_user_shortcuts_json',
                []
            );
            console.log('Keyboard shortcuts loaded:', this.shortcuts.length);
        } catch (error) {
            console.error('Failed to load keyboard shortcuts:', error);
        }
    }
    
    handleKeyPress(event) {
        const target = event.target;
        const tagName = target.tagName.toLowerCase();
        const isInput = ['input', 'textarea', 'select'].includes(tagName);
        const isContentEditable = target.isContentEditable;
        
        for (const shortcut of this.shortcuts) {
            if (this.matchesShortcut(event, shortcut)) {
                const context = this.getCurrentContext();
                
                if (!this.shouldApplyShortcut(shortcut, context, isInput, isContentEditable)) {
                    continue;
                }
                
                if (shortcut.prevent_default) {
                    event.preventDefault();
                }
                
                if (shortcut.stop_propagation) {
                    event.stopPropagation();
                }
                
                this.executeShortcut(shortcut, event, target);
                break;
            }
        }
    }
    
    matchesShortcut(event, shortcut) {
        const keyMatch = event.key.toLowerCase() === shortcut.key_code.toLowerCase() ||
                        event.code === shortcut.key_code;
        
        const ctrlMatch = event.ctrlKey === shortcut.ctrl_key;
        const altMatch = event.altKey === shortcut.alt_key;
        const shiftMatch = event.shiftKey === shortcut.shift_key;
        const metaMatch = event.metaKey === shortcut.meta_key;
        
        return keyMatch && ctrlMatch && altMatch && shiftMatch && metaMatch;
    }
    
    getCurrentContext() {
        const controller = this.env.__owl__;
        let viewType = 'unknown';
        let modelName = null;
        
        try {
            const actionService = this.action;
            const currentController = actionService.currentController;
            
            if (currentController && currentController.action) {
                viewType = currentController.action.type || 'unknown';
                modelName = currentController.action.res_model || null;
            }
            
            const activeElement = document.activeElement;
            if (activeElement) {
                const formView = activeElement.closest('.o_form_view');
                const listView = activeElement.closest('.o_list_view');
                const kanbanView = activeElement.closest('.o_kanban_view');
                
                if (formView) viewType = 'form';
                else if (listView) viewType = 'list';
                else if (kanbanView) viewType = 'kanban';
            }
        } catch (error) {
            console.debug('Could not determine context:', error);
        }
        
        return { viewType, modelName };
    }
    
    shouldApplyShortcut(shortcut, context, isInput, isContentEditable) {
        if (shortcut.apply_on_view !== 'all') {
            if (context.viewType !== shortcut.apply_on_view) {
                return false;
            }
        }
        
        if (shortcut.model_ids && shortcut.model_ids.length > 0) {
            if (!context.modelName || !shortcut.model_ids.includes(context.modelName)) {
                return false;
            }
        }
        
        return true;
    }
    
    executeShortcut(shortcut, event, target) {
        console.log('Executing shortcut:', shortcut.name, shortcut.action_code);
        
        try {
            switch (shortcut.action_code) {
                case 'next_field':
                    this.actionNextField(target);
                    break;
                case 'previous_field':
                    this.actionPreviousField(target);
                    break;
                case 'first_field':
                    this.actionFirstField();
                    break;
                case 'save_record':
                    this.actionSaveRecord();
                    break;
                case 'discard_changes':
                    this.actionDiscardChanges();
                    break;
                case 'edit_record':
                    this.actionEditRecord();
                    break;
                case 'new_line':
                    this.actionNewLine(event, target);
                    break;
                case 'tab_indent':
                    this.actionTabIndent(event, target);
                    break;
                case 'create_record':
                    this.actionCreateRecord();
                    break;
                case 'delete_record':
                    this.actionDeleteRecord();
                    break;
                case 'duplicate_record':
                    this.actionDuplicateRecord();
                    break;
                case 'close_dialog':
                    this.actionCloseDialog();
                    break;
                case 'search_focus':
                    this.actionSearchFocus();
                    break;
                default:
                    console.warn('Unknown action:', shortcut.action_code);
            }
        } catch (error) {
            console.error('Error executing shortcut:', error);
            this.notification.add('Error executing shortcut: ' + error.message, {
                type: 'danger',
            });
        }
    }
    
    actionNextField(currentTarget) {
        const formView = currentTarget.closest('.o_form_view');
        if (!formView) return;
        
        const inputs = Array.from(formView.querySelectorAll(
            'input:not([type="hidden"]):not([disabled]), textarea:not([disabled]), select:not([disabled])'
        )).filter(el => el.offsetParent !== null);
        
        const currentIndex = inputs.indexOf(currentTarget);
        if (currentIndex >= 0 && currentIndex < inputs.length - 1) {
            inputs[currentIndex + 1].focus();
        }
    }
    
    actionPreviousField(currentTarget) {
        const formView = currentTarget.closest('.o_form_view');
        if (!formView) return;
        
        const inputs = Array.from(formView.querySelectorAll(
            'input:not([type="hidden"]):not([disabled]), textarea:not([disabled]), select:not([disabled])'
        )).filter(el => el.offsetParent !== null);
        
        const currentIndex = inputs.indexOf(currentTarget);
        if (currentIndex > 0) {
            inputs[currentIndex - 1].focus();
        }
    }
    
    actionFirstField() {
        const formView = document.querySelector('.o_form_view');
        if (!formView) return;
        
        const firstInput = formView.querySelector(
            'input:not([type="hidden"]):not([disabled]), textarea:not([disabled]), select:not([disabled])'
        );
        if (firstInput) {
            firstInput.focus();
        }
    }
    
    actionSaveRecord() {
        const saveButton = document.querySelector('.o_form_button_save');
        if (saveButton && !saveButton.disabled) {
            saveButton.click();
        }
    }
    
    actionDiscardChanges() {
        const discardButton = document.querySelector('.o_form_button_cancel');
        if (discardButton) {
            discardButton.click();
        }
    }
    
    actionEditRecord() {
        const editButton = document.querySelector('.o_form_button_edit');
        if (editButton) {
            editButton.click();
        }
    }
    
    actionNewLine(event, target) {
        if (target.tagName.toLowerCase() === 'textarea') {
            const start = target.selectionStart;
            const end = target.selectionEnd;
            const value = target.value;
            
            target.value = value.substring(0, start) + '\n' + value.substring(end);
            target.selectionStart = target.selectionEnd = start + 1;
            
            const inputEvent = new Event('input', { bubbles: true });
            target.dispatchEvent(inputEvent);
        }
    }
    
    actionTabIndent(event, target) {
        if (target.tagName.toLowerCase() === 'textarea') {
            const start = target.selectionStart;
            const end = target.selectionEnd;
            const value = target.value;
            
            target.value = value.substring(0, start) + '\t' + value.substring(end);
            target.selectionStart = target.selectionEnd = start + 1;
            
            const inputEvent = new Event('input', { bubbles: true });
            target.dispatchEvent(inputEvent);
        }
    }
    
    actionCreateRecord() {
        const createButton = document.querySelector('.o_list_button_add, .o-kanban-button-new');
        if (createButton) {
            createButton.click();
        }
    }
    
    actionDeleteRecord() {
        const deleteButton = document.querySelector('.o_form_button_delete');
        if (deleteButton) {
            deleteButton.click();
        }
    }
    
    actionDuplicateRecord() {
        const actionMenu = document.querySelector('.o_cp_action_menus button');
        if (actionMenu) {
            actionMenu.click();
            setTimeout(() => {
                const duplicateItem = Array.from(document.querySelectorAll('.dropdown-item'))
                    .find(el => el.textContent.includes('Duplicate'));
                if (duplicateItem) {
                    duplicateItem.click();
                }
            }, 100);
        }
    }
    
    actionCloseDialog() {
        const closeButton = document.querySelector('.modal .btn-close, .o_dialog_close');
        if (closeButton) {
            closeButton.click();
        }
    }
    
    actionSearchFocus() {
        const searchInput = document.querySelector('.o_searchview_input');
        if (searchInput) {
            searchInput.focus();
        }
    }
}

ShortcutManager.template = "keyboard_shortcuts_config.ShortcutManager";

export const shortcutManagerService = {
    dependencies: ["orm", "action", "notification"],
    async start(env, { orm, action, notification }) {
        const manager = {
            shortcuts: [],
            
            async loadShortcuts() {
                try {
                    this.shortcuts = await orm.call(
                        'keyboard.shortcut',
                        'get_user_shortcuts_json',
                        []
                    );
                    console.log('Keyboard shortcuts loaded:', this.shortcuts.length);
                } catch (error) {
                    console.error('Failed to load keyboard shortcuts:', error);
                }
            },
            
            async reload() {
                await this.loadShortcuts();
            }
        };
        
        await manager.loadShortcuts();
        
        document.addEventListener('keydown', (event) => {
            const target = event.target;
            const tagName = target.tagName.toLowerCase();
            const isInput = ['input', 'textarea', 'select'].includes(tagName);
            
            for (const shortcut of manager.shortcuts) {
                if (matchesShortcut(event, shortcut)) {
                    const context = getCurrentContext();
                    
                    if (!shouldApplyShortcut(shortcut, context, isInput)) {
                        continue;
                    }
                    
                    if (shortcut.prevent_default) {
                        event.preventDefault();
                    }
                    
                    if (shortcut.stop_propagation) {
                        event.stopPropagation();
                    }
                    
                    executeShortcut(shortcut, event, target, { orm, action, notification });
                    break;
                }
            }
        }, true);
        
        return manager;
    }
};

function matchesShortcut(event, shortcut) {
    const keyMatch = event.key.toLowerCase() === shortcut.key_code.toLowerCase() ||
                    event.code === shortcut.key_code;
    
    const ctrlMatch = event.ctrlKey === shortcut.ctrl_key;
    const altMatch = event.altKey === shortcut.alt_key;
    const shiftMatch = event.shiftKey === shortcut.shift_key;
    const metaMatch = event.metaKey === shortcut.meta_key;
    
    return keyMatch && ctrlMatch && altMatch && shiftMatch && metaMatch;
}

function getCurrentContext() {
    let viewType = 'unknown';
    let modelName = null;
    
    try {
        const activeElement = document.activeElement;
        if (activeElement) {
            const formView = activeElement.closest('.o_form_view');
            const listView = activeElement.closest('.o_list_view');
            const kanbanView = activeElement.closest('.o_kanban_view');
            
            if (formView) viewType = 'form';
            else if (listView) viewType = 'list';
            else if (kanbanView) viewType = 'kanban';
        }
    } catch (error) {
        console.debug('Could not determine context:', error);
    }
    
    return { viewType, modelName };
}

function shouldApplyShortcut(shortcut, context, isInput) {
    if (shortcut.apply_on_view !== 'all') {
        if (context.viewType !== shortcut.apply_on_view) {
            return false;
        }
    }
    
    if (shortcut.model_ids && shortcut.model_ids.length > 0) {
        if (!context.modelName || !shortcut.model_ids.includes(context.modelName)) {
            return false;
        }
    }
    
    return true;
}

function executeShortcut(shortcut, event, target, services) {
    console.log('Executing shortcut:', shortcut.name, shortcut.action_code);
    
    try {
        switch (shortcut.action_code) {
            case 'next_field':
                actionNextField(target);
                break;
            case 'previous_field':
                actionPreviousField(target);
                break;
            case 'first_field':
                actionFirstField();
                break;
            case 'save_record':
                actionSaveRecord();
                break;
            case 'discard_changes':
                actionDiscardChanges();
                break;
            case 'edit_record':
                actionEditRecord();
                break;
            case 'new_line':
                actionNewLine(event, target);
                break;
            case 'tab_indent':
                actionTabIndent(event, target);
                break;
            case 'create_record':
                actionCreateRecord();
                break;
            case 'delete_record':
                actionDeleteRecord();
                break;
            case 'duplicate_record':
                actionDuplicateRecord();
                break;
            case 'close_dialog':
                actionCloseDialog();
                break;
            case 'search_focus':
                actionSearchFocus();
                break;
            default:
                console.warn('Unknown action:', shortcut.action_code);
        }
    } catch (error) {
        console.error('Error executing shortcut:', error);
    }
}

function actionNextField(currentTarget) {
    const formView = currentTarget.closest('.o_form_view');
    if (!formView) return;
    
    const inputs = Array.from(formView.querySelectorAll(
        'input:not([type="hidden"]):not([disabled]):not([readonly]), textarea:not([disabled]):not([readonly]), select:not([disabled])'
    )).filter(el => el.offsetParent !== null);
    
    const currentIndex = inputs.indexOf(currentTarget);
    if (currentIndex >= 0 && currentIndex < inputs.length - 1) {
        inputs[currentIndex + 1].focus();
        if (inputs[currentIndex + 1].select) {
            inputs[currentIndex + 1].select();
        }
    }
}

function actionPreviousField(currentTarget) {
    const formView = currentTarget.closest('.o_form_view');
    if (!formView) return;
    
    const inputs = Array.from(formView.querySelectorAll(
        'input:not([type="hidden"]):not([disabled]):not([readonly]), textarea:not([disabled]):not([readonly]), select:not([disabled])'
    )).filter(el => el.offsetParent !== null);
    
    const currentIndex = inputs.indexOf(currentTarget);
    if (currentIndex > 0) {
        inputs[currentIndex - 1].focus();
        if (inputs[currentIndex - 1].select) {
            inputs[currentIndex - 1].select();
        }
    }
}

function actionFirstField() {
    const formView = document.querySelector('.o_form_view');
    if (!formView) return;
    
    const firstInput = formView.querySelector(
        'input:not([type="hidden"]):not([disabled]):not([readonly]), textarea:not([disabled]):not([readonly]), select:not([disabled])'
    );
    if (firstInput) {
        firstInput.focus();
        if (firstInput.select) {
            firstInput.select();
        }
    }
}

function actionSaveRecord() {
    const saveButton = document.querySelector('.o_form_button_save');
    if (saveButton && !saveButton.disabled) {
        saveButton.click();
    }
}

function actionDiscardChanges() {
    const discardButton = document.querySelector('.o_form_button_cancel');
    if (discardButton) {
        discardButton.click();
    }
}

function actionEditRecord() {
    const editButton = document.querySelector('.o_form_button_edit');
    if (editButton) {
        editButton.click();
    }
}

function actionNewLine(event, target) {
    if (target.tagName.toLowerCase() === 'textarea') {
        const start = target.selectionStart;
        const end = target.selectionEnd;
        const value = target.value;
        
        target.value = value.substring(0, start) + '\n' + value.substring(end);
        target.selectionStart = target.selectionEnd = start + 1;
        
        const inputEvent = new Event('input', { bubbles: true });
        target.dispatchEvent(inputEvent);
    }
}

function actionTabIndent(event, target) {
    if (target.tagName.toLowerCase() === 'textarea') {
        const start = target.selectionStart;
        const end = target.selectionEnd;
        const value = target.value;
        
        target.value = value.substring(0, start) + '\t' + value.substring(end);
        target.selectionStart = target.selectionEnd = start + 1;
        
        const inputEvent = new Event('input', { bubbles: true });
        target.dispatchEvent(inputEvent);
    }
}

function actionCreateRecord() {
    const createButton = document.querySelector('.o_list_button_add, .o-kanban-button-new');
    if (createButton) {
        createButton.click();
    }
}

function actionDeleteRecord() {
    const deleteButton = document.querySelector('.o_form_button_delete');
    if (deleteButton) {
        deleteButton.click();
    }
}

function actionDuplicateRecord() {
    const actionMenu = document.querySelector('.o_cp_action_menus button');
    if (actionMenu) {
        actionMenu.click();
        setTimeout(() => {
            const duplicateItem = Array.from(document.querySelectorAll('.dropdown-item'))
                .find(el => el.textContent.includes('Duplicate'));
            if (duplicateItem) {
                duplicateItem.click();
            }
        }, 100);
    }
}

function actionCloseDialog() {
    const closeButton = document.querySelector('.modal .btn-close, .o_dialog_close');
    if (closeButton) {
        closeButton.click();
    }
}

function actionSearchFocus() {
    const searchInput = document.querySelector('.o_searchview_input');
    if (searchInput) {
        searchInput.focus();
    }
}

registry.category("services").add("shortcut_manager", shortcutManagerService);
