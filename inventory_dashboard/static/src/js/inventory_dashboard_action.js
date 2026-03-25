/** @odoo-module **/

import { useSetupAction } from "@web/webclient/actions/action_hook";
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

/**
 * Client action that displays the Inventory Dashboard in an iframe
 * so the user stays inside the Odoo web client and keeps the sidebar/menus.
 */
export class InventoryDashboardIframeAction extends Component {
    setup() {
        useSetupAction();
        this.dashboardUrl = "/inventory_dashboard";
    }
}
InventoryDashboardIframeAction.template = "inventory_dashboard.InventoryDashboardIframeAction";

registry.category("actions").add("inventory_dashboard_iframe", InventoryDashboardIframeAction);
