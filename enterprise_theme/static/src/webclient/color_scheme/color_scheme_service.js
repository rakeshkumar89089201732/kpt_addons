/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";

import { switchColorSchemeItem } from "./color_scheme_menu_items";

const serviceRegistry = registry.category("services");
const userMenuRegistry = registry.category("user_menuitems");

export const colorSchemeService = {
    dependencies: ["ui"],

    start(env, { ui }) {
        userMenuRegistry.add("color_scheme.switch", switchColorSchemeItem, { force: true });
        return {
            switchToColorScheme: (scheme) => {
                cookie.set("color_scheme", scheme);
                ui.block();
                this.reload();
            },
        };
    },
    reload() {
        browser.location.reload();
    },
};

// Override web_enterprise's color_scheme when both are installed (force: true)
serviceRegistry.add("color_scheme", colorSchemeService, { force: true });
