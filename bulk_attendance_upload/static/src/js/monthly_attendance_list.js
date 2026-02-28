/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";
import { DynamicRecordList } from "@web/model/relational_model/dynamic_record_list";

patch(ListController.prototype, {
    /**
     * Override to force inline creation in editable list views for monthly attendance wizard
     * Even when grouped, we want to add records inline at the root level
     */
    async createRecord({ group } = {}) {
        if (this.props.resModel === 'monthly.attendance.set.wizard') {
            const list = (group && group.list) || this.model.root;
            // Force inline creation even when grouped - add to root list
            if (this.editable && this.model.root instanceof DynamicRecordList) {
                await this.model.root.leaveEditMode();
                if (!this.model.root.editedRecord) {
                    // Add new record at bottom (editable="bottom")
                    await this.model.root.addNewRecord(false);
                }
                this.render();
                return;
            }
        }
        return super.createRecord({ group });
    }
});
