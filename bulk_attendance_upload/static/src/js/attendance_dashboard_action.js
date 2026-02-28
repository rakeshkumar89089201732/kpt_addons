/** @odoo-module **/

import { useSetupAction } from "@web/webclient/actions/action_hook";
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

/**
 * Client action that displays the Attendance Dashboard in an iframe
 * so the user stays inside the Odoo web client and keeps the sidebar/menus.
 */
export class AttendanceDashboardIframeAction extends Component {
    setup() {
        useSetupAction();
        this.dashboardUrl = "/attendance/dashboard";
    }
}
AttendanceDashboardIframeAction.template = "bulk_attendance_upload.AttendanceDashboardIframeAction";

registry.category("actions").add("attendance_dashboard_iframe", AttendanceDashboardIframeAction);
