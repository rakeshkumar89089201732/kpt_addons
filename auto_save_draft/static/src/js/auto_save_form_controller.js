/** @odoo-module **/
import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const AUTO_SAVE_MODELS = ["sale.order", "stock.picking"];
const DEFAULT_INITIAL_DELAY = 120000; // 2 minutes
const DEFAULT_REGULAR_INTERVAL = 240000; // 4 minutes

patch(FormController.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this._autoSaveTimer = null;
        this._isFirstSave = true;
        this._partnerWatcherActive = false;
        this._autoSaveConfig = {
            enabled: true,
            initialDelay: DEFAULT_INITIAL_DELAY,
            regularInterval: DEFAULT_REGULAR_INTERVAL,
        };

        onMounted(() => {
            this._bootstrapAutoSave();
        });

        onWillUnmount(() => {
            this._clearAutoSaveTimer();
        });
    },

    async _bootstrapAutoSave() {
        if (!AUTO_SAVE_MODELS.includes(this.props.resModel)) {
            return;
        }
        await this._loadAutoSaveConfig();
        if (!this._autoSaveConfig.enabled) {
            return;
        }

        const record = this.model.root;
        if (!record.resId) {
            this._watchPartnerField();
        } else {
            this._startAutoSave(this._autoSaveConfig.initialDelay);
        }
    },

    async _loadAutoSaveConfig() {
        try {
            const params = await this.orm.call("auto.save.draft.config", "get_params", []);
            this._autoSaveConfig.enabled = !!params.enabled;
            this._autoSaveConfig.initialDelay = params.initial_delay_ms || DEFAULT_INITIAL_DELAY;
            this._autoSaveConfig.regularInterval = params.regular_interval_ms || DEFAULT_REGULAR_INTERVAL;
        } catch {
            // keep defaults
        }
    },

    _watchPartnerField() {
        if (this._partnerWatcherActive) return;
        this._partnerWatcherActive = true;

        const record = this.model.root;
        
        // Watch for changes using model's update mechanism
        const originalUpdate = record.update.bind(record);
        record.update = async (changes) => {
            const result = await originalUpdate(changes);
            
            // Check if partner_id was set
            if (changes.partner_id && !record.resId) {
                const partnerId = Array.isArray(changes.partner_id) 
                    ? changes.partner_id[0] 
                    : changes.partner_id;
                
                if (partnerId) {
                    setTimeout(() => this._saveNewRecord(), 100); // Small delay for other onchanges
                }
            }
            
            return result;
        };
    },

    async _saveNewRecord() {
        const record = this.model?.root;
        if (!record || record.resId) return; // Already saved
        
        try {
            await record.save({ stayInEdition: true });
            
            // Start auto-save timer after first save
            this._isFirstSave = false;
            this._partnerWatcherActive = false; // Stop watching
            this._startAutoSave(this._autoSaveConfig.regularInterval);
        } catch (error) {
            // ignore: autosave should never block the UI
        }
    },

    _startAutoSave(interval) {
        this._clearAutoSaveTimer();
        this._autoSaveTimer = setInterval(() => {
            this._autoSave();
        }, interval);
    },

    _clearAutoSaveTimer() {
        if (this._autoSaveTimer) {
            clearInterval(this._autoSaveTimer);
            this._autoSaveTimer = null;
        }
    },

    async _autoSave() {
        const record = this.model?.root;
        if (!record || !record.resId) return;
        if (!record.isDirty) return; // No changes
        if (record.data.state && record.data.state !== "draft") return;

        try {
            await record.save({ stayInEdition: true });
        } catch (error) {
            // ignore: autosave should never block the UI
        }
    },
});
