/** @odoo-module */

import { NavBar } from "@web/webclient/navbar/navbar";
import { registry } from "@web/core/registry";
const { fuzzyLookup } = require('@web/core/utils/search');
import { computeAppsAndMenuItems } from "@web/webclient/menus/menu_helpers";
import { onMounted } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";


patch(NavBar.prototype, {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    setup() {
        super.setup()
        this._search_def = $.Deferred();
        let { apps, menuItems } = computeAppsAndMenuItems(this.menuService.getMenuAsTree("root"));
        this._apps = apps;
        this._searchableMenus = menuItems;
        this.user_id = session.uid;
        this.session = session;
        onMounted(this.onMounted);
    },

    onMounted() {
        this.$search_container = $(".search-container");
        this.$search_input = $(".search-input input");
        this.$search_results = $(".search-results");
        this.$app_menu = $(".app-menu");
        this.$dropdown_menu = $(".dropdown-menu");
        this.$cybro_main_menu = $(".cybro-main-menu");
        const $appmenu = $("#Appmenu");
        const closeSidebar = () => {
            $appmenu.removeClass("show");
        };
        if (this.$cybro_main_menu.length) {
            this.$cybro_main_menu.on("click", "a.o_app", () => {
                closeSidebar();
            });
        }
        $(document).on("click.dodgerblue", (ev) => {
            if ($(ev.target).closest("#Appmenu, [data-bs-target='#Appmenu']").length === 0) {
                closeSidebar();
            }
        });
        $(window).on("hashchange.dodgerblue", () => {
            closeSidebar();
        });
        $(document).on("keydown.dodgerblue", (ev) => {
            if (ev.key === "Escape") {
                closeSidebar();
            }
        });
        const $ptoTitleCandidates = $("div,section,article").filter(function () {
            const t = $(this).text();
            return /\bPaid Time Off\b/i.test(t);
        });
        const $ptoCard = $ptoTitleCandidates.first();
        if ($ptoCard.length) {
            $ptoCard.addClass("dodger-pto-card");
            $ptoCard.find("h1,h2,.o_stat_value").addClass("dodger-pto-value");
            $ptoCard.find("h3,h4,h5,small,span").addClass("dodger-pto-title");
        }
        let enhanceScheduled = false;
        const enhanceSystray = () => {
            enhanceScheduled = false;
            $(".o_menu_systray i.fa.fa-circle").each(function () {
                const $dot = $(this);
                const $btn = $dot.closest("a,button");
                if (!$btn.length) return;
                if ($btn.attr("data-dodger-enhanced") === "1") return;
                $btn.attr("data-dodger-enhanced", "1").addClass("dodger-attendance-btn");
                let $label = $btn.find(".dodger-attendance-label");
                if (!$label.length) {
                    $label = $("<span class='dodger-attendance-label'/>");
                    $dot.after($label);
                }
                const updateBtnState = () => {
                    const isIn = $dot.hasClass("text-success") || $dot.hasClass("o-success");
                    $btn.toggleClass("dodger-attendance-in", isIn);
                    $btn.toggleClass("dodger-attendance-out", !isIn);
                    $label.text(isIn ? "IN" : "OUT");
                    $btn.attr("aria-label", isIn ? "Checked in" : "Checked out");
                };
                updateBtnState();
                try {
                    const observer = new MutationObserver(updateBtnState);
                    observer.observe($dot.get(0), { attributes: true, attributeFilter: ["class"] });
                } catch (e) {
                    setInterval(updateBtnState, 1000);
                }
            });
        };
        const scheduleEnhance = () => {
            if (enhanceScheduled) return;
            enhanceScheduled = true;
            setTimeout(() => requestAnimationFrame(enhanceSystray), 50);
        };
        scheduleEnhance();
        const systrayEl = document.querySelector(".o_menu_systray");
        if (systrayEl) {
            try {
                const systrayObserver = new MutationObserver(() => scheduleEnhance());
                systrayObserver.observe(systrayEl, { childList: true, subtree: true });
            } catch (e) {
                setInterval(scheduleEnhance, 500);
            }
        }
        const $sidebar = $(".cybro-sidebar-qweb");
        if ($sidebar.length) {
            $sidebar.on("mouseenter", () => document.body.classList.add("dodger-sidebar-open"));
            $sidebar.on("mouseleave", () => document.body.classList.remove("dodger-sidebar-open"));
        }

        // Comprehensive active menu highlighting
        const highlightActiveMenu = () => {
            // Remove all previous active classes
            $(".o_menu_sections .o_nav_entry, .o_menu_sections .dropdown-toggle, .o_menu_sections a").removeClass("active");

            let foundActive = false;

            // Strategy 1: Check for Odoo's native active/selected classes
            const $odooActive = $(".o_menu_sections .o-dropdown.show, .o_menu_sections button[aria-expanded='true']");
            if ($odooActive.length) {
                $odooActive.addClass("active");
                foundActive = true;
            }

            // Strategy 2: Parse URL hash for menu_id
            if (!foundActive) {
                const hash = window.location.hash;
                const menuMatch = hash.match(/menu_id=(\d+)/);

                if (menuMatch) {
                    const currentMenuId = parseInt(menuMatch[1]);

                    // Check all menu sections links
                    $(".o_menu_sections a, .o_menu_sections button").each(function () {
                        const $item = $(this);
                        const itemMenuId = parseInt($item.attr("data-menu-id") || $item.data("menu-id") || "0");

                        if (itemMenuId === currentMenuId) {
                            $item.addClass("active");
                            // Also add to parent if it's a dropdown toggle
                            $item.closest(".o-dropdown, .dropdown").find(".dropdown-toggle").addClass("active");
                            foundActive = true;
                            return false;
                        }

                        // Check if this is a parent menu of the current menu
                        const $dropdown = $item.closest(".o-dropdown, .dropdown");
                        if ($dropdown.length) {
                            $dropdown.find(".dropdown-menu a").each(function () {
                                const $subItem = $(this);
                                const subMenuId = parseInt($subItem.attr("data-menu-id") || $subItem.data("menu-id") || "0");
                                if (subMenuId === currentMenuId) {
                                    $item.addClass("active");
                                    $dropdown.find(".dropdown-toggle").addClass("active");
                                    foundActive = true;
                                    return false;
                                }
                            });
                        }
                    });
                }
            }

            // Strategy 3: Use menuService as fallback
            if (!foundActive) {
                try {
                    const currentMenu = this.menuService?.getCurrentApp?.();
                    if (currentMenu?.id) {
                        $(".o_menu_sections a, .o_menu_sections button").each(function () {
                            const $item = $(this);
                            const itemMenuId = parseInt($item.attr("data-menu-id") || $item.data("menu-id") || "0");
                            if (itemMenuId === currentMenu.id) {
                                $item.addClass("active");
                                $item.closest(".o-dropdown, .dropdown").find(".dropdown-toggle").addClass("active");
                                return false;
                            }
                        });
                    }
                } catch (e) {
                    // Silently fail
                }
            }
        };

        // Initial highlight with delay to ensure DOM is ready
        setTimeout(() => highlightActiveMenu(), 300);

        // Re-highlight on hash changes
        $(window).on("hashchange.dodger-active-menu", () => {
            setTimeout(highlightActiveMenu, 100);
        });

        // Watch for DOM mutations in the navbar (for dynamic menu changes)
        const observeNavbar = () => {
            const navbarEl = document.querySelector(".o_menu_sections");
            if (navbarEl) {
                const observer = new MutationObserver(() => {
                    setTimeout(highlightActiveMenu, 50);
                });
                observer.observe(navbarEl, {
                    childList: true,
                    subtree: true,
                    attributes: true,
                    attributeFilter: ["class", "aria-expanded"]
                });
            }
        };
        setTimeout(observeNavbar, 500);

        var navbar = $(".o_main_navbar");
        var self = this;
    },
    _searchMenusSchedule: function () {
        this.$search_results.removeClass("o_hidden")
        this.$app_menu.addClass("o_hidden");
        this._search_def.reject();
        this._search_def = $.Deferred();
        setTimeout(this._search_def.resolve.bind(this._search_def), 50);
        this._search_def.done(this._searchMenus.bind(this));
    },
    _searchMenus: function () {
        var query = this.$search_input.val();
        if (query === "") {
            this.$search_container.removeClass("has-results");
            this.$app_menu.removeClass("o_hidden");
            this.$search_results.empty();
            return;
        }
        var results = [];
        fuzzyLookup(query, this._apps, (menu) => menu.label)
            .forEach((menu) => {
                results.push({
                    category: "apps",
                    name: menu.label,
                    actionID: menu.actionID,
                    id: menu.id,
                    webIconData: menu.webIconData,
                });
            });

        fuzzyLookup(query, this._searchableMenus, (menu) =>
            (menu.parents + " / " + menu.label).split("/").reverse().join("/")
        ).forEach((menu) => {
            results.push({
                category: "menu_items",
                name: menu.parents + " / " + menu.label,
                actionID: menu.actionID,
                id: menu.id,
            });
        });

        this.$search_container.toggleClass(
            "has-results",
            Boolean(results.length)
        );
        var resultsHtml = ""
        this.$search_results.empty();
        results.forEach(function (result) {
            resultsHtml += "<div class='search_icons'><a class='o-menu-search-result dropdown-item col-12 ml-auto mr-auto'  style=\"background-image:url('data:image/png;base64," + result["webIconData"] + "')\" href='web#action=" + result["actionID"] + "&menu_id=" + result["id"] + "'>" + result["name"] + "</a></div>"
        })
        this.$search_results.append(resultsHtml);
    },
});
