/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";

patch(ListController.prototype, {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.userService = useService("user");
    },

    get showCreateMonthlyAttendanceButton() {
        // Only show for hr.attendance model
        if (this.props.resModel !== "hr.attendance") {
            return false;
        }
        // Check if user has the group - use async check
        try {
            return this.userService.hasGroup("bulk_attendance_upload.group_create_monthly_attendance");
        } catch (e) {
            return false;
        }
    },

    async onCreateMonthlyAttendance() {
        const action = {
            name: "Create Monthly Attendance",
            res_model: "monthly.attendance.config.wizard",
            views: [[false, "form"]],
            target: "new",
            type: "ir.actions.act_window",
            context: {},
        };
        await this.actionService.doAction(action);
    },
});
