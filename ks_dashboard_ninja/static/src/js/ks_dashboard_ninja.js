/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { formatDateTime, formatDate } from "@web/core/l10n/dates";
import { session } from "@web/session";
import { KsChartComponent } from "./ks_chart_component";

export class KsDashboardNinja extends Component {
    setup() {
        // Services
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.notificationService = useService("notification");
        this.rpc = useService("rpc");
        this.userService = useService("user");
        
        // DOM reference
        this.rootRef = useRef("root");

        // State management
        this.state = useState({
            dashboard_data: {},
            dashboard_mode: true,
            edit_mode: false,
            date_filter_data: {},
            date_filter_selection: {},
            gridstack_config: {},
            dashboard_id: null,
            controller_id: null,
            ks_dashboard_manager: false,
            ks_dashboard_list: [],
            ks_dashboard_item_length: 0,
            ks_gridstack_grid: null,
            ks_update_interval: null,
            ks_chart_color_options: [
                "#F04F65", "#f69032", "#fdc233", "#53cfce", "#36a2eb", "#8a79fd",
                "#b1b5be", "#1c425c", "#8c2620", "#71ecef", "#0b4295", "#f2e6ce"
            ]
        });

        // Properties
        this.ks_dashboard_id = this.props.dashboard_id || false;
        this.controller_id = this.props.controller_id || false;
        
        // File type detection
        this.file_type_magic_word = {
            '/': 'jpg',
            'R': 'gif', 
            'i': 'png',
            'P': 'svg+xml',
        };

        // Date filter configurations
        this.ks_date_filter_selections = [
            'l_day', 't_week', 't_month', 't_quarter', 't_year',
            'td_last_7_days', 'td_last_30_days', 'td_last_90_days', 
            'td_last_365_days', 'ls_day', 'ls_week', 'ls_month', 
            'ls_quarter', 'ls_year', 'l_week', 'l_month', 'l_quarter', 
            'l_year', 'ls_past_until_now', 'ls_pastyear_until_now',
            'n_day', 'n_week', 'n_month', 'n_quarter', 'n_year'
        ];

        this.ks_date_filter_selection_order = [
            'l_day', 't_week', 't_month', 't_quarter', 't_year'
        ];

        // GridStack options
        this.gridstack_options = {
            staticGrid: true,
            float: false,
            cellHeight: 108,
            styleInHead: true,
            rtl: false,
            animate: true,
        };

        // Date formatters
        this.date_format = session.user_context.lang === 'en_US' ? 'MM/DD/YYYY' : 'DD/MM/YYYY';
        this.datetime_format = session.user_context.lang === 'en_US' ? 'MM/DD/YYYY hh:mm:ss' : 'DD/MM/YYYY hh:mm:ss';

        // Lifecycle hooks
        onWillStart(this.onWillStart);
        onMounted(this.onMounted);
        onWillUnmount(this.onWillUnmount);
    }

    async onWillStart() {
        await this.getContext();
        await this.ks_fetch_data();
    }

    onMounted() {
        // Ensure DOM is ready before rendering
        if (this.rootRef.el) {
            this.ksRenderDashboard();
            this.ks_set_update_interval();
            this.initializeDateFilter();
        } else {
            // Fallback: wait for next tick
            setTimeout(() => {
                if (this.rootRef.el) {
                    this.ksRenderDashboard();
                    this.ks_set_update_interval();
                    this.initializeDateFilter();
                }
            }, 0);
        }
        
        // Add event listeners
        document.addEventListener('keydown', this.onKeyDown.bind(this));
        window.addEventListener('resize', this.onWindowResize.bind(this));
    }

    onWillUnmount() {
        this.ks_remove_update_interval();
        
        // Remove event listeners
        document.removeEventListener('keydown', this.onKeyDown.bind(this));
        window.removeEventListener('resize', this.onWindowResize.bind(this));
        
        // Save layout before unmounting
        if (this.state.ks_gridstack_grid) {
            this._ksSaveCurrentLayout();
        }
        
        // Clean up GridStack
        if (this.gridstack) {
            this.gridstack.destroy();
        }
    }

    async getContext() {
        const context = this.props.context || {};
        this.state.dashboard_id = context.ks_dashboard_id || this.ks_dashboard_id;
        this.state.controller_id = context.controller_id || this.controller_id;
        
        // Set dashboard manager permissions
        this.state.ks_dashboard_manager = await this.userService.hasGroup('ks_dashboard_ninja.ks_dashboard_ninja_group_manager');
    }

    async ks_fetch_data() {
        if (!this.state.dashboard_id) return;

        try {
            const result = await this.rpc("/web/dataset/call_kw", {
                model: 'ks_dashboard_ninja.board',
                method: 'ks_fetch_dashboard_data',
                args: [this.state.dashboard_id],
                kwargs: {
                    context: session.user_context,
                }
            });

            this.state.dashboard_data = result;
            this.state.ks_dashboard_item_length = Object.keys(result.ks_item_data || {}).length;
            
            // Initialize date filter data
            if (result.ks_dashboard_date_filter_data) {
                this.state.date_filter_data = result.ks_dashboard_date_filter_data;
                this.state.date_filter_selection = result.ks_dashboard_date_filter_selection || {};
            }

            // Initialize gridstack config
            if (result.ks_gridstack_config) {
                this.state.gridstack_config = JSON.parse(result.ks_gridstack_config);
            }

        } catch (error) {
            console.error("Error fetching dashboard data:", error);
            this.notificationService.add(_t("Error loading dashboard data"), { type: "danger" });
        }
    }

    async ks_fetch_items_data() {
        if (!this.state.dashboard_id) return;

        try {
            const result = await this.rpc("/web/dataset/call_kw", {
                model: 'ks_dashboard_ninja.board',
                method: 'ks_fetch_item_data',
                args: [this.state.dashboard_id],
                kwargs: {
                    ks_dashboard_date_filter_data: this.state.date_filter_data,
                    context: session.user_context,
                }
            });

            if (result && result.ks_item_data) {
                this.state.dashboard_data.ks_item_data = result.ks_item_data;
                this.ksRenderDashboardItems();
            }

        } catch (error) {
            console.error("Error fetching items data:", error);
        }
    }

    ks_set_update_interval() {
        if (this.state.dashboard_data.ks_set_interval && this.state.dashboard_data.ks_set_interval > 0) {
            this.state.ks_update_interval = setInterval(() => {
                this.ksFetchUpdateItem();
            }, this.state.dashboard_data.ks_set_interval);
        }
    }

    ks_remove_update_interval() {
        if (this.state.ks_update_interval) {
            clearInterval(this.state.ks_update_interval);
            this.state.ks_update_interval = null;
        }
    }

    ksRenderDashboard() {
        if (!this.rootRef.el) return;
        const dashboardContainer = this.rootRef.el.querySelector('.ks_dashboard_container');
        if (!dashboardContainer) return;

        // Clear existing content
        dashboardContainer.innerHTML = '';

        // Render dashboard header
        this.ksRenderDashboardHeader();

        // Render dashboard items
        this.ksRenderDashboardItems();

        // Initialize GridStack if in edit mode
        if (this.state.edit_mode) {
            this.ksInitializeGridStack();
        }
    }

    ksRenderDashboardHeader() {
        if (!this.rootRef.el) return;
        const headerContainer = this.rootRef.el.querySelector('.ks_dashboard_header');
        if (!headerContainer || !this.state.dashboard_data) return;

        const headerData = {
            dashboard_name: this.state.dashboard_data.name || _t('Dashboard'),
            dashboard_menu: this.state.dashboard_data.ks_dashboard_menu_name || '',
            date_filter: this.state.dashboard_data.ks_dashboard_date_filter_data || {},
            dashboard_manager: this.state.ks_dashboard_manager,
        };

        // Render header template (this would be implemented with OWL templates)
        headerContainer.innerHTML = this.renderHeaderTemplate(headerData);
    }

    ksRenderDashboardItems() {
        if (!this.rootRef.el) return;
        const itemsContainer = this.rootRef.el.querySelector('.ks_dashboard_items_container');
        if (!itemsContainer || !this.state.dashboard_data.ks_item_data) return;

        itemsContainer.innerHTML = '';

        Object.values(this.state.dashboard_data.ks_item_data).forEach(item => {
            const itemElement = this.ksRenderDashboardItem(item);
            if (itemElement) {
                itemsContainer.appendChild(itemElement);
            }
        });
    }

    ksRenderDashboardItem(item) {
        if (!item || !item.id) return null;

        const itemContainer = document.createElement('div');
        itemContainer.className = `ks_dashboard_item ks_dashboard_item_${item.id}`;
        itemContainer.setAttribute('data-item-id', item.id);

        // Set grid stack attributes if available
        if (this.state.gridstack_config[item.id]) {
            const config = this.state.gridstack_config[item.id];
            itemContainer.setAttribute('gs-x', config.x || 0);
            itemContainer.setAttribute('gs-y', config.y || 0);
            itemContainer.setAttribute('gs-w', config.w || 4);
            itemContainer.setAttribute('gs-h', config.h || 4);
        }

        // Render based on item type
        switch (item.ks_dashboard_item_type) {
            case 'ks_kpi':
                this.ksRenderKpiItem(itemContainer, item);
                break;
            case 'ks_list_view':
                this.ksRenderListItem(itemContainer, item);
                break;
            case 'ks_chart_item':
                this.ksRenderChartItem(itemContainer, item);
                break;
            case 'ks_tile':
                this.ksRenderTileItem(itemContainer, item);
                break;
            default:
                console.warn(`Unknown item type: ${item.ks_dashboard_item_type}`);
                return null;
        }

        return itemContainer;
    }

    ksRenderKpiItem(container, item) {
        if (!item.ks_record_count && item.ks_record_count !== 0) {
            this.ksRenderEmptyItem(item, container, 'No KPI data available');
            return;
        }

        try {
            container.className = 'ks_kpi_item h-100 card';
            
            // Calculate KPI values
            const kpiData = this.calculateKpiData(item);
            
            // Create KPI header
            const headerDiv = document.createElement('div');
            headerDiv.className = 'ks_kpi_header d-flex justify-content-between align-items-center p-2 border-bottom';
            headerDiv.innerHTML = `
                <h6 class="mb-0">${item.name || 'KPI'}</h6>
                ${this.state.edit_mode ? '<button class="btn btn-sm btn-outline-secondary"><i class="fa fa-edit"></i></button>' : ''}
            `;
            
            // Create KPI content
            const contentDiv = document.createElement('div');
            contentDiv.className = 'ks_kpi_content p-3 text-center h-100 d-flex flex-column justify-content-center';
            contentDiv.style.backgroundColor = item.ks_background_color || '#ffffff';
            contentDiv.style.color = item.ks_font_color || '#000000';
            
            // Add icon if configured
            let iconHtml = '';
            if (item.ks_icon) {
                const iconColor = item.ks_default_icon_color || '#007bff';
                iconHtml = `
                    <div class="ks_kpi_icon mb-2">
                        <i class="${item.ks_icon} fa-2x" style="color: ${iconColor}"></i>
                    </div>
                `;
            }
            
            // Format KPI value
            const formattedValue = this.formatKpiValue(kpiData.value, item);
            
            // Create KPI content HTML
            let kpiContentHtml = `
                ${iconHtml}
                <div class="ks_kpi_value_section">
                    <h2 class="ks_kpi_value mb-1" title="${kpiData.tooltip || kpiData.value}">
                        ${formattedValue}
                    </h2>
                    <small class="ks_kpi_label text-muted">
                        ${item.ks_model_display_name || 'Records'}
                    </small>
                </div>
            `;
            
            // Add target comparison if enabled
            if (item.ks_goal_enable && item.ks_goal_value) {
                const targetData = this.calculateTargetComparison(kpiData.value, item.ks_goal_value, item);
                kpiContentHtml += `
                    <div class="ks_kpi_target mt-2">
                        <div class="d-flex justify-content-between align-items-center">
                            <small class="text-muted">Target: ${this.formatKpiValue(item.ks_goal_value, item)}</small>
                            <span class="ks_target_deviation" style="color: ${targetData.color}">
                                <i class="fa fa-arrow-${targetData.arrow}"></i>
                                ${targetData.deviation}
                            </span>
                        </div>
                        ${this.renderTargetProgress(targetData, item)}
                    </div>
                `;
            }
            
            // Add second KPI if configured
            if (item.ks_model_id_2 && (item.ks_record_count_2 || item.ks_record_count_2 === 0)) {
                const kpi2Data = this.calculateKpiData(item, true);
                const comparison = this.calculateKpiComparison(kpiData.value, kpi2Data.value, item);
                
                kpiContentHtml += `
                    <div class="ks_kpi_comparison mt-2 pt-2 border-top">
                        <div class="row">
                            <div class="col-6 text-center">
                                <small class="text-muted d-block">${item.ks_model_display_name}</small>
                                <strong>${formattedValue}</strong>
                            </div>
                            <div class="col-6 text-center">
                                <small class="text-muted d-block">${item.ks_model_display_name_2}</small>
                                <strong>${this.formatKpiValue(kpi2Data.value, item)}</strong>
                            </div>
                        </div>
                        <div class="text-center mt-1">
                            <span style="color: ${comparison.color}">
                                <i class="fa fa-arrow-${comparison.arrow}"></i>
                                ${comparison.percentage}
                            </span>
                        </div>
                    </div>
                `;
            }
            
            contentDiv.innerHTML = kpiContentHtml;
            
            container.appendChild(headerDiv);
            container.appendChild(contentDiv);
            
        } catch (error) {
            console.error('Error rendering KPI item:', error);
            this.ksRenderEmptyItem(item, container, 'Error loading KPI data');
        }
    }

    /**
     * Calculate KPI data
     */
    calculateKpiData(item, isSecondKpi = false) {
        const suffix = isSecondKpi ? '_2' : '';
        let value = isSecondKpi ? item.ks_record_count_2 : item.ks_record_count;
        
        // Apply multiplier if configured
        if (item.ks_multiplier_active && item.ks_multiplier) {
            value = value * item.ks_multiplier;
        }
        
        return {
            value: value,
            tooltip: this.formatNumber(value, 'exact', item.ks_precision_digits || 2)
        };
    }

    /**
     * Format KPI value
     */
    formatKpiValue(value, item) {
        if (typeof value !== 'number') {
            return value;
        }
        
        const format = item.ks_data_format || 'global';
        const precision = item.ks_precision_digits || 2;
        
        return this.formatNumber(value, format, precision);
    }

    /**
     * Calculate target comparison
     */
    calculateTargetComparison(currentValue, targetValue, item) {
        const difference = targetValue - currentValue;
        const isPositive = difference <= 0;
        const deviation = targetValue === 0 ? 0 : Math.round(Math.abs(difference / targetValue) * 100);
        const progress = targetValue === 0 ? 0 : Math.round((currentValue / targetValue) * 100);
        
        return {
            color: isPositive ? 'green' : 'red',
            arrow: isPositive ? 'up' : 'down',
            deviation: deviation === Infinity ? '∞' : `${deviation}%`,
            progress: progress,
            progressFormatted: `${progress}%`
        };
    }

    /**
     * Calculate KPI comparison between two values
     */
    calculateKpiComparison(value1, value2, item) {
        if (value2 === 0) {
            return {
                color: 'gray',
                arrow: 'right',
                percentage: 'N/A'
            };
        }
        
        const percentage = Math.round(((value1 - value2) / value2) * 100);
        const isPositive = percentage >= 0;
        
        return {
            color: isPositive ? 'green' : 'red',
            arrow: isPositive ? 'up' : 'down',
            percentage: `${Math.abs(percentage)}%`
        };
    }

    /**
     * Render target progress bar or number
     */
    renderTargetProgress(targetData, item) {
        if (item.ks_target_view === 'Progress Bar') {
            return `
                <div class="progress mt-2" style="height: 8px;">
                    <div class="progress-bar" 
                         role="progressbar" 
                         style="width: ${Math.min(targetData.progress, 100)}%; background-color: ${targetData.color};"
                         aria-valuenow="${targetData.progress}" 
                         aria-valuemin="0" 
                         aria-valuemax="100">
                    </div>
                </div>
                <small class="text-muted">${targetData.progressFormatted}</small>
            `;
        } else {
            return `<small class="text-muted">${targetData.progressFormatted} of target</small>`;
        }
    }

    ksRenderListItem(container, item) {
        if (!item.ks_list_view_data) {
            this.ksRenderEmptyItem(item, container, 'No list data available');
            return;
        }

        try {
            const listData = JSON.parse(item.ks_list_view_data);
            
            container.className = 'ks_list_item h-100 card';
            
            // Create list header
            const headerDiv = document.createElement('div');
            headerDiv.className = 'ks_list_header d-flex justify-content-between align-items-center p-2 border-bottom';
            headerDiv.innerHTML = `
                <h6 class="mb-0">${item.name || 'List View'}</h6>
                <div class="ks_list_controls">
                    ${item.ks_record_count ? `<small class="text-muted">${item.ks_record_count} records</small>` : ''}
                    ${this.state.edit_mode ? '<button class="btn btn-sm btn-outline-secondary ml-2"><i class="fa fa-edit"></i></button>' : ''}
                </div>
            `;
            
            // Create list content
            const contentDiv = document.createElement('div');
            contentDiv.className = 'ks_list_content p-2 h-100 overflow-auto';
            
            if (listData && listData.data_rows && listData.data_rows.length > 0) {
                const table = this.createListTable(listData, item);
                contentDiv.appendChild(table);
                
                // Add pagination if needed
                if (item.ks_record_count && item.ks_record_count > listData.data_rows.length) {
                    const pagination = this.createListPagination(item, listData);
                    contentDiv.appendChild(pagination);
                }
            } else {
                contentDiv.innerHTML = `
                    <div class="text-center text-muted py-4">
                        <i class="fa fa-list fa-3x mb-3"></i>
                        <p>No data available</p>
                    </div>
                `;
            }
            
            container.appendChild(headerDiv);
            container.appendChild(contentDiv);
            
        } catch (error) {
            console.error('Error rendering list item:', error);
            this.ksRenderEmptyItem(item, container, 'Error loading list data');
        }
    }

    /**
     * Create list table
     */
    createListTable(listData, item) {
        const table = document.createElement('table');
        table.className = 'table table-sm table-hover mb-0';
        
        // Create table header
        const thead = document.createElement('thead');
        thead.className = 'table-light';
        const headerRow = document.createElement('tr');
        
        if (listData.labels) {
            listData.labels.forEach(label => {
                const th = document.createElement('th');
                th.textContent = label;
                th.style.fontSize = '12px';
                headerRow.appendChild(th);
            });
        }
        
        thead.appendChild(headerRow);
        table.appendChild(thead);
        
        // Create table body
        const tbody = document.createElement('tbody');
        
        if (listData.data_rows) {
            listData.data_rows.forEach((row, index) => {
                const tr = document.createElement('tr');
                tr.style.cursor = 'pointer';
                
                // Add click handler for drill-down
                tr.addEventListener('click', () => {
                    this.onListRowClick(item, row, index);
                });
                
                if (row.data) {
                    row.data.forEach((cellData, cellIndex) => {
                        const td = document.createElement('td');
                        td.style.fontSize = '11px';
                        
                        // Format cell data based on field type
                        const formattedData = this.formatListCellData(cellData, listData.fields_type?.[cellIndex]);
                        td.innerHTML = formattedData;
                        
                        tr.appendChild(td);
                    });
                }
                
                tbody.appendChild(tr);
            });
        }
        
        table.appendChild(tbody);
        return table;
    }

    /**
     * Format list cell data
     */
    formatListCellData(data, fieldType) {
        if (data === null || data === undefined || data === false) {
            return '<span class="text-muted">-</span>';
        }
        
        if (typeof data === 'number') {
            if (fieldType === 'monetary') {
                return this.formatCurrency(data);
            } else if (fieldType === 'float') {
                return data.toFixed(2);
            } else {
                return data.toLocaleString();
            }
        }
        
        if (fieldType === 'date' || fieldType === 'datetime') {
            return this.formatDate(data, fieldType);
        }
        
        if (typeof data === 'string' && data.length > 50) {
            return `<span title="${data}">${data.substring(0, 47)}...</span>`;
        }
        
        return data.toString();
    }

    /**
     * Format currency value
     */
    formatCurrency(value) {
        // Use session currency or default formatting
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(value);
    }

    /**
     * Format date value
     */
    formatDate(value, fieldType) {
        try {
            const date = new Date(value);
            if (fieldType === 'date') {
                return date.toLocaleDateString();
            } else {
                return date.toLocaleString();
            }
        } catch (error) {
            return value;
        }
    }

    /**
     * Create list pagination
     */
    createListPagination(item, listData) {
        const paginationDiv = document.createElement('div');
        paginationDiv.className = 'd-flex justify-content-between align-items-center mt-2 pt-2 border-top';
        
        const currentCount = listData.data_rows ? listData.data_rows.length : 0;
        const totalCount = item.ks_record_count || currentCount;
        
        paginationDiv.innerHTML = `
            <small class="text-muted">
                Showing ${currentCount} of ${totalCount} records
            </small>
            <div class="btn-group btn-group-sm">
                <button class="btn btn-outline-secondary" onclick="this.loadMoreListData('${item.id}')">
                    <i class="fa fa-refresh"></i> Load More
                </button>
            </div>
        `;
        
        return paginationDiv;
    }

    /**
     * Handle list row click for drill-down
     */
    onListRowClick(item, row, index) {
        if (this.state.edit_mode) return;
        
        console.log('List row clicked:', item.id, row, index);
        // TODO: Implement drill-down functionality
        // This would typically open a form view or filter related data
    }

    /**
     * Load more list data
     */
    loadMoreListData(itemId) {
        console.log('Loading more data for item:', itemId);
        // TODO: Implement pagination/load more functionality
        // This would fetch additional records and update the list
    }

    ksRenderChartItem(container, item) {
        if (!item.ks_chart_data) {
            this.ksRenderEmptyItem(item, container, 'No chart data available');
            return;
        }

        try {
            const chartData = JSON.parse(item.ks_chart_data);
            const chartType = item.ks_dashboard_item_type;
            
            container.className = 'ks_chart_item h-100 card';
            
            // Create chart header
            const headerDiv = document.createElement('div');
            headerDiv.className = 'ks_chart_header d-flex justify-content-between align-items-center p-2 border-bottom';
            headerDiv.innerHTML = `
                <h6 class="mb-0">${item.name || 'Chart'}</h6>
                ${this.state.edit_mode ? '<button class="btn btn-sm btn-outline-secondary"><i class="fa fa-edit"></i></button>' : ''}
            `;
            
            // Create chart content container
            const contentDiv = document.createElement('div');
            contentDiv.className = 'ks_chart_content p-2 h-100';
            contentDiv.style.height = '300px';
            
            // Create canvas element
            const canvas = document.createElement('canvas');
            canvas.id = `ks_chart_${item.id}`;
            canvas.className = 'w-100 h-100';
            
            contentDiv.appendChild(canvas);
            container.appendChild(headerDiv);
            container.appendChild(contentDiv);
            
            // Initialize chart after DOM is ready
            setTimeout(() => {
                this.ksInitializeChart(item, chartData, chartType, canvas);
            }, 100);
            
        } catch (error) {
            console.error('Error rendering chart item:', error);
            this.ksRenderEmptyItem(item, container, 'Error loading chart');
        }
    }

    ksRenderTileItem(container, item) {
        if (!item.ks_record_count && item.ks_record_count !== 0) {
            this.ksRenderEmptyItem(item, container, 'No tile data available');
            return;
        }

        try {
            container.className = 'ks_tile_item h-100 card';
            
            // Calculate tile data
            const tileData = this.calculateTileData(item);
            
            // Determine tile layout
            const layout = item.ks_tile_layout || 'default';
            
            // Create tile content based on layout
            const tileContent = this.createTileContent(tileData, item, layout);
            
            container.appendChild(tileContent);
            
            // Add click handler if configured
            if (item.ks_action) {
                container.style.cursor = 'pointer';
                container.addEventListener('click', () => this.onTileClick(item));
            }
            
        } catch (error) {
            console.error('Error rendering tile item:', error);
            this.ksRenderEmptyItem(item, container, 'Error loading tile data');
        }
    }

    /**
     * Calculate tile data with formatting
     */
    calculateTileData(item) {
        let value = item.ks_record_count || 0;
        
        // Apply multiplier if configured
        if (item.ks_multiplier_active && item.ks_multiplier) {
            value = value * item.ks_multiplier;
        }
        
        return {
            value: value,
            formattedValue: this.formatTileValue(value, item),
            tooltip: this.formatNumber(value, 'exact', item.ks_precision_digits || 2)
        };
    }

    /**
     * Format tile value
     */
    formatTileValue(value, item) {
        if (typeof value !== 'number') {
            return value;
        }
        
        const format = item.ks_data_format || 'global';
        const precision = item.ks_precision_digits || 2;
        
        return this.formatNumber(value, format, precision);
    }

    /**
     * Create tile content based on layout
     */
    createTileContent(tileData, item, layout) {
        const contentDiv = document.createElement('div');
        contentDiv.className = 'ks_tile_content h-100 d-flex';
        contentDiv.style.backgroundColor = item.ks_background_color || '#f8f9fa';
        contentDiv.style.color = item.ks_font_color || '#000000';
        contentDiv.title = tileData.tooltip;
        
        switch (layout) {
            case 'layout1':
                return this.createLayout1Tile(contentDiv, tileData, item);
            case 'layout2':
                return this.createLayout2Tile(contentDiv, tileData, item);
            case 'layout3':
                return this.createLayout3Tile(contentDiv, tileData, item);
            case 'layout4':
                return this.createLayout4Tile(contentDiv, tileData, item);
            default:
                return this.createDefaultTile(contentDiv, tileData, item);
        }
    }

    /**
     * Default tile layout - centered content
     */
    createDefaultTile(contentDiv, tileData, item) {
        contentDiv.className += ' flex-column justify-content-center align-items-center text-center p-3';
        
        let iconHtml = '';
        if (item.ks_icon) {
            const iconColor = item.ks_default_icon_color || '#007bff';
            iconHtml = `
                <div class="ks_tile_icon mb-2">
                    <i class="${item.ks_icon} fa-3x" style="color: ${iconColor}"></i>
                </div>
            `;
        }
        
        contentDiv.innerHTML = `
            ${iconHtml}
            <div class="ks_tile_value_section">
                <h1 class="ks_tile_value mb-1 font-weight-bold">${tileData.formattedValue}</h1>
                <h6 class="ks_tile_title mb-0 text-muted">${item.name || 'Tile'}</h6>
            </div>
            ${this.state.edit_mode ? '<div class="ks_tile_actions mt-2"><button class="btn btn-sm btn-outline-secondary"><i class="fa fa-edit"></i></button></div>' : ''}
        `;
        
        return contentDiv;
    }

    /**
     * Layout 1 - Icon on left, content on right
     */
    createLayout1Tile(contentDiv, tileData, item) {
        contentDiv.className += ' flex-row align-items-center p-3';
        
        let iconHtml = '';
        if (item.ks_icon) {
            const iconColor = item.ks_default_icon_color || '#007bff';
            iconHtml = `
                <div class="ks_tile_icon me-3">
                    <i class="${item.ks_icon} fa-2x" style="color: ${iconColor}"></i>
                </div>
            `;
        }
        
        contentDiv.innerHTML = `
            ${iconHtml}
            <div class="ks_tile_content_right flex-grow-1">
                <h3 class="ks_tile_value mb-0 font-weight-bold">${tileData.formattedValue}</h3>
                <small class="ks_tile_title text-muted">${item.name || 'Tile'}</small>
            </div>
        `;
        
        return contentDiv;
    }

    /**
     * Layout 2 - Content on left, icon on right
     */
    createLayout2Tile(contentDiv, tileData, item) {
        contentDiv.className += ' flex-row align-items-center p-3';
        
        let iconHtml = '';
        if (item.ks_icon) {
            const iconColor = item.ks_default_icon_color || '#007bff';
            iconHtml = `
                <div class="ks_tile_icon ms-3">
                    <i class="${item.ks_icon} fa-2x" style="color: ${iconColor}"></i>
                </div>
            `;
        }
        
        contentDiv.innerHTML = `
            <div class="ks_tile_content_left flex-grow-1">
                <h3 class="ks_tile_value mb-0 font-weight-bold">${tileData.formattedValue}</h3>
                <small class="ks_tile_title text-muted">${item.name || 'Tile'}</small>
            </div>
            ${iconHtml}
        `;
        
        return contentDiv;
    }

    /**
     * Layout 3 - Icon on top, content below
     */
    createLayout3Tile(contentDiv, tileData, item) {
        contentDiv.className += ' flex-column justify-content-center align-items-center text-center p-3';
        
        let iconHtml = '';
        if (item.ks_icon) {
            const iconColor = item.ks_default_icon_color || '#007bff';
            iconHtml = `
                <div class="ks_tile_icon mb-2">
                    <i class="${item.ks_icon} fa-4x" style="color: ${iconColor}"></i>
                </div>
            `;
        }
        
        contentDiv.innerHTML = `
            ${iconHtml}
            <div class="ks_tile_content_bottom">
                <h2 class="ks_tile_value mb-1 font-weight-bold">${tileData.formattedValue}</h2>
                <h6 class="ks_tile_title mb-0">${item.name || 'Tile'}</h6>
            </div>
        `;
        
        return contentDiv;
    }

    /**
     * Layout 4 - Compact layout with small icon
     */
    createLayout4Tile(contentDiv, tileData, item) {
        contentDiv.className += ' flex-column justify-content-between p-2';
        
        let iconHtml = '';
        if (item.ks_icon) {
            const iconColor = item.ks_default_icon_color || '#007bff';
            iconHtml = `<i class="${item.ks_icon}" style="color: ${iconColor}"></i>`;
        }
        
        contentDiv.innerHTML = `
            <div class="ks_tile_header d-flex justify-content-between align-items-center">
                <small class="ks_tile_title text-muted">${item.name || 'Tile'}</small>
                ${iconHtml}
            </div>
            <div class="ks_tile_value_section text-center">
                <h2 class="ks_tile_value mb-0 font-weight-bold">${tileData.formattedValue}</h2>
            </div>
        `;
        
        return contentDiv;
    }

    /**
     * Handle tile click events
     */
    onTileClick(item) {
        if (item.ks_action) {
            this.actionService.doAction(item.ks_action, {
                additionalContext: this.getContext()
            });
        }
    }

    ksInitializeChart(item, chartData, chartType, canvas) {
        // Chart initialization logic would go here
        // This would use Chart.js or similar charting library
        console.log('Initializing chart for item:', item.id, 'with type:', chartType);
        
        // Basic chart configuration
        const config = {
            type: this.getChartJSType(chartType),
            data: this.formatChartData(chartData, item),
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: false
                    }
                }
            }
        };
        
        // Initialize Chart.js if available
        if (typeof Chart !== 'undefined') {
            new Chart(canvas, config);
        }
    }
    
    getChartJSType(dashboardItemType) {
        const typeMapping = {
            'ks_bar_chart': 'bar',
            'ks_line_chart': 'line',
            'ks_pie_chart': 'pie',
            'ks_doughnut_chart': 'doughnut',
            'ks_area_chart': 'line',
            'ks_scatter_chart': 'scatter'
        };
        return typeMapping[dashboardItemType] || 'bar';
    }
    
    formatChartData(chartData, item) {
        // Format data for Chart.js
        return {
            labels: chartData.labels || [],
            datasets: [{
                label: item.name || 'Data',
                data: chartData.values || [],
                backgroundColor: this.getChartColors(chartData.values?.length || 1),
                borderColor: this.getChartColors(chartData.values?.length || 1, 0.8),
                borderWidth: 1
            }]
        };
    }
    
    getChartColors(count, alpha = 0.6) {
        const colors = this.state.ks_chart_color_options;
        const result = [];
        for (let i = 0; i < count; i++) {
            const color = colors[i % colors.length];
            result.push(alpha < 1 ? this.hexToRgba(color, alpha) : color);
        }
        return result;
    }
    
    hexToRgba(hex, alpha) {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }
    
    ksRenderEmptyItem(item, container, message) {
        container.className = 'ks_empty_item h-100 card d-flex align-items-center justify-content-center';
        container.innerHTML = `
            <div class="text-center text-muted">
                <i class="fa fa-chart-bar fa-3x mb-3"></i>
                <p>${message}</p>
                <small>${item.name || 'Dashboard Item'}</small>
            </div>
        `;
    }

    ksInitializeGridStack() {
        // GridStack initialization for edit mode
        if (typeof GridStack !== 'undefined') {
            this.state.ks_gridstack_grid = GridStack.init(this.gridstack_options);
        }
    }

    async ksFetchUpdateItem() {
        // Update individual items
        console.log('Updating dashboard items');
        await this.ks_fetch_items_data();
    }

    async _ksSaveCurrentLayout() {
        if (!this.state.ks_gridstack_grid || !this.state.dashboard_id) return;

        try {
            const serializedData = this.state.ks_gridstack_grid.save();
            await this.rpc("/web/dataset/call_kw", {
                model: 'ks_dashboard_ninja.board',
                method: 'write',
                args: [[this.state.dashboard_id], {
                    ks_gridstack_config: JSON.stringify(serializedData)
                }],
                kwargs: { context: session.user_context }
            });
        } catch (error) {
            console.error("Error saving layout:", error);
        }
    }

    // Template rendering methods (these would be replaced with OWL templates)
    renderHeaderTemplate(data) {
        return `
            <div class="ks_dashboard_header_container">
                <h2 class="ks_dashboard_name">${data.dashboard_name}</h2>
                <div class="ks_dashboard_controls">
                    ${data.dashboard_manager ? '<button class="btn btn-primary ks_dashboard_edit_btn">Edit</button>' : ''}
                </div>
            </div>
        `;
    }

    renderKpiTemplate(data) {
        return `
            <div class="ks_kpi_container" style="background-color: ${data.ks_background_color || '#ffffff'}; color: ${data.ks_font_color || '#000000'};">
                <div class="ks_kpi_header">
                    <h4 class="ks_kpi_name">${data.name}</h4>
                </div>
                <div class="ks_kpi_content">
                    <div class="ks_kpi_value">${this.ksNumFormatter(data.ks_record_count, 2)}</div>
                    ${data.ks_icon ? `<i class="${data.ks_icon}" style="color: ${data.ks_default_icon_color || '#000000'};"></i>` : ''}
                </div>
            </div>
        `;
    }

    renderListTemplate(data) {
        return `
            <div class="ks_list_container">
                <div class="ks_list_header">
                    <h4 class="ks_list_name">${data.name}</h4>
                </div>
                <div class="ks_list_content">
                    <div class="ks_list_view_data">
                        <!-- List data would be rendered here -->
                        <p>Records: ${data.ks_record_count}</p>
                    </div>
                </div>
            </div>
        `;
    }

    renderChartTemplate(data) {
        return `
            <div class="ks_chart_container">
                <div class="ks_chart_header">
                    <h4 class="ks_chart_name">${data.name}</h4>
                </div>
                <div class="ks_chart_content">
                    <canvas class="ks_chart_canvas" data-chart-id="${data.item_id}"></canvas>
                </div>
            </div>
        `;
    }

    renderTileTemplate(data) {
        return `
            <div class="ks_tile_container" style="background-color: ${data.ks_background_color || '#ffffff'}; color: ${data.ks_font_color || '#000000'};">
                <div class="ks_tile_header">
                    <h4 class="ks_tile_name">${data.name}</h4>
                </div>
                <div class="ks_tile_content">
                    <div class="ks_tile_value">${this.ksNumFormatter(data.ks_record_count, 2)}</div>
                    ${data.ks_icon ? `<i class="${data.ks_icon}" style="color: ${data.ks_default_icon_color || '#000000'};"></i>` : ''}
                </div>
            </div>
        `;
    }

    // Utility methods
    ksNumFormatter(num, digits) {
        const si = [
            { value: 1, symbol: "" },
            { value: 1E3, symbol: "k" },
            { value: 1E6, symbol: "M" },
            { value: 1E9, symbol: "G" },
            { value: 1E12, symbol: "T" },
            { value: 1E15, symbol: "P" },
            { value: 1E18, symbol: "E" }
        ];

        const negative = num < 0;
        if (negative) num = Math.abs(num);

        const rx = /\.0+$|(\.[0-9]*[1-9])0+$/;
        let i;
        for (i = si.length - 1; i > 0; i--) {
            if (num >= si[i].value) {
                break;
            }
        }

        const result = (num / si[i].value).toFixed(digits).replace(rx, "$1") + si[i].symbol;
        return negative ? "-" + result : result;
    }

    /**
     * Format number based on format type
     */
    formatNumber(value, format, precision = 2) {
        if (typeof value !== 'number' || isNaN(value)) {
            return value;
        }

        switch (format) {
            case 'exact':
                return value.toLocaleString(undefined, {
                    minimumFractionDigits: precision,
                    maximumFractionDigits: precision
                });
            case 'global':
            case 'compact':
                return this.ksNumFormatter(value, precision);
            case 'percentage':
                return (value * 100).toFixed(precision) + '%';
            case 'currency':
                return this.formatCurrency(value);
            default:
                return this.ksNumFormatter(value, precision);
        }
    }

    // Event handlers
    onEditModeToggle(ev) {
        if (ev) ev.stopPropagation();
        this.state.edit_mode = !this.state.edit_mode;
        this.ksRenderDashboard();
        
        // Show/hide edit controls
        this.toggleEditControls();
        
        // Save layout if exiting edit mode
        if (!this.state.edit_mode && this.gridstack) {
            this._ksSaveCurrentLayout();
        }
    }

    onDateFilterChange(filterData) {
        this.state.date_filter_data = filterData;
        this.state.date_filter_selection = filterData.selection || {};
        this.ks_fetch_items_data();
    }

    /**
     * Initialize date filter UI
     */
    initializeDateFilter() {
        const filterContainer = document.querySelector('.ks_date_filter_container');
        if (!filterContainer) return;

        const filterSelect = this.createDateFilterSelect();
        const customDateInputs = this.createCustomDateInputs();
        
        filterContainer.appendChild(filterSelect);
        filterContainer.appendChild(customDateInputs);
    }

    /**
     * Create date filter dropdown
     */
    createDateFilterSelect() {
        const select = document.createElement('select');
        select.className = 'ks_date_filter_select form-control';
        select.addEventListener('change', this.onDateFilterSelectChange.bind(this));

        // Add default option
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = _t('Select Date Filter');
        select.appendChild(defaultOption);

        // Add predefined date filter options
        const filterOptions = {
            'l_day': _t('Today'),
            'l_week': _t('This Week'),
            'l_month': _t('This Month'),
            'l_quarter': _t('This Quarter'),
            'l_year': _t('This Year'),
            'ls_day': _t('Yesterday'),
            'ls_week': _t('Last Week'),
            'ls_month': _t('Last Month'),
            'ls_quarter': _t('Last Quarter'),
            'ls_year': _t('Last Year'),
            'td_last_7_days': _t('Last 7 Days'),
            'td_last_30_days': _t('Last 30 Days'),
            'td_last_90_days': _t('Last 90 Days'),
            'td_last_365_days': _t('Last 365 Days'),
            'n_day': _t('Tomorrow'),
            'n_week': _t('Next Week'),
            'n_month': _t('Next Month'),
            'n_quarter': _t('Next Quarter'),
            'n_year': _t('Next Year'),
            'custom': _t('Custom Range')
        };

        Object.entries(filterOptions).forEach(([value, text]) => {
            const option = document.createElement('option');
            option.value = value;
            option.textContent = text;
            select.appendChild(option);
        });

        return select;
    }

    /**
     * Create custom date input fields
     */
    createCustomDateInputs() {
        const container = document.createElement('div');
        container.className = 'ks_custom_date_inputs d-none';

        const startDateInput = document.createElement('input');
        startDateInput.type = 'date';
        startDateInput.className = 'form-control ks_start_date';
        startDateInput.placeholder = _t('Start Date');
        startDateInput.addEventListener('change', this.onCustomDateChange.bind(this));

        const endDateInput = document.createElement('input');
        endDateInput.type = 'date';
        endDateInput.className = 'form-control ks_end_date';
        endDateInput.placeholder = _t('End Date');
        endDateInput.addEventListener('change', this.onCustomDateChange.bind(this));

        const applyButton = document.createElement('button');
        applyButton.className = 'btn btn-primary ks_apply_date_filter';
        applyButton.textContent = _t('Apply');
        applyButton.addEventListener('click', this.applyCustomDateFilter.bind(this));

        container.appendChild(startDateInput);
        container.appendChild(endDateInput);
        container.appendChild(applyButton);

        return container;
    }

    /**
     * Handle date filter selection change
     */
    onDateFilterSelectChange(event) {
        const selection = event.target.value;
        const customInputs = document.querySelector('.ks_custom_date_inputs');

        if (selection === 'custom') {
            customInputs.classList.remove('d-none');
        } else {
            customInputs.classList.add('d-none');
            if (selection) {
                this.applyPredefinedDateFilter(selection);
            }
        }
    }

    /**
     * Apply predefined date filter
     */
    applyPredefinedDateFilter(selection) {
        const dateRange = this.calculateDateRange(selection);
        const filterData = {
            selection: selection,
            start_date: dateRange.start_date,
            end_date: dateRange.end_date
        };

        this.onDateFilterChange(filterData);
    }

    /**
     * Calculate date range based on selection
     */
    calculateDateRange(selection) {
        const today = new Date();
        let startDate, endDate;

        switch (selection) {
            case 'l_day':
                startDate = endDate = new Date(today);
                break;
            case 'l_week':
                startDate = new Date(today.setDate(today.getDate() - today.getDay()));
                endDate = new Date(today.setDate(today.getDate() + 6));
                break;
            case 'l_month':
                startDate = new Date(today.getFullYear(), today.getMonth(), 1);
                endDate = new Date(today.getFullYear(), today.getMonth() + 1, 0);
                break;
            case 'l_quarter':
                const quarter = Math.floor(today.getMonth() / 3);
                startDate = new Date(today.getFullYear(), quarter * 3, 1);
                endDate = new Date(today.getFullYear(), quarter * 3 + 3, 0);
                break;
            case 'l_year':
                startDate = new Date(today.getFullYear(), 0, 1);
                endDate = new Date(today.getFullYear(), 11, 31);
                break;
            case 'ls_day':
                startDate = endDate = new Date(today.setDate(today.getDate() - 1));
                break;
            case 'ls_week':
                const lastWeekStart = new Date(today.setDate(today.getDate() - today.getDay() - 7));
                startDate = lastWeekStart;
                endDate = new Date(lastWeekStart.setDate(lastWeekStart.getDate() + 6));
                break;
            case 'ls_month':
                startDate = new Date(today.getFullYear(), today.getMonth() - 1, 1);
                endDate = new Date(today.getFullYear(), today.getMonth(), 0);
                break;
            case 'ls_quarter':
                const lastQuarter = Math.floor(today.getMonth() / 3) - 1;
                startDate = new Date(today.getFullYear(), lastQuarter * 3, 1);
                endDate = new Date(today.getFullYear(), lastQuarter * 3 + 3, 0);
                break;
            case 'ls_year':
                startDate = new Date(today.getFullYear() - 1, 0, 1);
                endDate = new Date(today.getFullYear() - 1, 11, 31);
                break;
            case 'td_last_7_days':
                startDate = new Date(today.setDate(today.getDate() - 7));
                endDate = new Date();
                break;
            case 'td_last_30_days':
                startDate = new Date(today.setDate(today.getDate() - 30));
                endDate = new Date();
                break;
            case 'td_last_90_days':
                startDate = new Date(today.setDate(today.getDate() - 90));
                endDate = new Date();
                break;
            case 'td_last_365_days':
                startDate = new Date(today.setDate(today.getDate() - 365));
                endDate = new Date();
                break;
            case 'n_day':
                startDate = endDate = new Date(today.setDate(today.getDate() + 1));
                break;
            case 'n_week':
                const nextWeekStart = new Date(today.setDate(today.getDate() - today.getDay() + 7));
                startDate = nextWeekStart;
                endDate = new Date(nextWeekStart.setDate(nextWeekStart.getDate() + 6));
                break;
            case 'n_month':
                startDate = new Date(today.getFullYear(), today.getMonth() + 1, 1);
                endDate = new Date(today.getFullYear(), today.getMonth() + 2, 0);
                break;
            case 'n_quarter':
                const nextQuarter = Math.floor(today.getMonth() / 3) + 1;
                startDate = new Date(today.getFullYear(), nextQuarter * 3, 1);
                endDate = new Date(today.getFullYear(), nextQuarter * 3 + 3, 0);
                break;
            case 'n_year':
                startDate = new Date(today.getFullYear() + 1, 0, 1);
                endDate = new Date(today.getFullYear() + 1, 11, 31);
                break;
            default:
                startDate = endDate = new Date();
        }

        return {
            start_date: this.formatDateForServer(startDate),
            end_date: this.formatDateForServer(endDate)
        };
    }

    /**
     * Handle custom date input changes
     */
    onCustomDateChange(event) {
        // Validate date range
        const startDateInput = document.querySelector('.ks_start_date');
        const endDateInput = document.querySelector('.ks_end_date');
        const applyButton = document.querySelector('.ks_apply_date_filter');

        if (startDateInput.value && endDateInput.value) {
            const startDate = new Date(startDateInput.value);
            const endDate = new Date(endDateInput.value);
            
            if (startDate <= endDate) {
                applyButton.disabled = false;
                endDateInput.setCustomValidity('');
            } else {
                applyButton.disabled = true;
                endDateInput.setCustomValidity(_t('End date must be after start date'));
            }
        } else {
            applyButton.disabled = true;
        }
    }

    /**
     * Apply custom date filter
     */
    applyCustomDateFilter() {
        const startDateInput = document.querySelector('.ks_start_date');
        const endDateInput = document.querySelector('.ks_end_date');

        if (startDateInput.value && endDateInput.value) {
            const filterData = {
                selection: 'custom',
                start_date: startDateInput.value,
                end_date: endDateInput.value
            };

            this.onDateFilterChange(filterData);
        }
    }

    /**
     * Format date for server
     */
    formatDateForServer(date) {
        return date.toISOString().split('T')[0];
    }

    /**
     * Clear date filter
     */
    clearDateFilter() {
        const filterSelect = document.querySelector('.ks_date_filter_select');
        const customInputs = document.querySelector('.ks_custom_date_inputs');

        if (filterSelect) {
            filterSelect.value = '';
        }
        if (customInputs) {
            customInputs.classList.add('d-none');
            customInputs.querySelector('.ks_start_date').value = '';
            customInputs.querySelector('.ks_end_date').value = '';
        }

        this.state.date_filter_data = {};
        this.state.date_filter_selection = {};
        this.ks_fetch_items_data();
    }

    /**
     * Toggle edit controls visibility
     */
    toggleEditControls() {
        const editControls = document.querySelectorAll('.ks_edit_control');
        editControls.forEach(control => {
            control.style.display = this.state.edit_mode ? 'block' : 'none';
        });
    }

    /**
     * Handle dashboard item click events
     */
    onDashboardItemClick(event, item) {
        event.preventDefault();
        event.stopPropagation();
        
        if (this.state.edit_mode) {
            this.onEditItem(event, item);
        } else if (item.ks_action) {
            this.onItemAction(item);
        }
    }

    /**
     * Handle item action execution
     */
    onItemAction(item) {
        try {
            if (item.ks_action) {
                const context = {
                    ...this.getContext(),
                    ks_dashboard_id: this.props.dashboard_id,
                    ks_item_id: item.id
                };
                
                this.actionService.doAction(item.ks_action, {
                    additionalContext: context
                });
            }
        } catch (error) {
            console.error('Error executing item action:', error);
            this.notificationService.add('Error executing action', { type: 'danger' });
        }
    }

    /**
     * Handle edit item
     */
    onEditItem(ev, item) {
        if (ev) ev.stopPropagation();
        
        const context = {
            ...this.getContext(),
            default_ks_dashboard_id: this.props.dashboard_id
        };
        
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'ks_dashboard_ninja.item',
            res_id: item.id,
            views: [[false, 'form']],
            target: 'new',
            context: context
        });
    }

    /**
     * Handle refresh dashboard
     */
    onRefreshDashboard(ev) {
        if (ev) ev.stopPropagation();
        this.state.loading = true;
        this.ks_fetch_items_data().finally(() => {
            this.state.loading = false;
        });
    }

    /**
     * Handle refresh single item
     */
    onRefreshItem(ev, item) {
        if (ev) ev.stopPropagation();
        this.ksFetchUpdateItem(item.id);
    }

    /**
     * Handle add new item
     */
    onAddItem(ev) {
        if (ev) ev.stopPropagation();
        const context = {
            ...this.getContext(),
            default_ks_dashboard_id: this.props.dashboard_id
        };
        
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'ks_dashboard_ninja.item',
            views: [[false, 'form']],
            target: 'new',
            context: context
        });
    }

    /**
     * Handle duplicate item
     */
    onDuplicateItem(ev, item) {
        if (ev) ev.stopPropagation();
        
        const context = {
            ...this.getContext(),
            default_ks_dashboard_id: this.props.dashboard_id
        };
        
        this.rpc('/web/dataset/call_kw/ks_dashboard_ninja.item/copy', {
            model: 'ks_dashboard_ninja.item',
            method: 'copy',
            args: [item.id],
            kwargs: { context: context }
        }).then(() => {
            this.notificationService.add('Item duplicated successfully', { type: 'success' });
            this.ks_fetch_items_data();
        }).catch(error => {
            console.error('Error duplicating item:', error);
            this.notificationService.add('Error duplicating item', { type: 'danger' });
        });
    }

    /**
     * Handle delete item
     */
    onDeleteItem(ev, item) {
        if (ev) ev.stopPropagation();
        
        this.dialogService.add(ConfirmationDialog, {
            title: 'Delete Item',
            body: `Are you sure you want to delete "${item.name}"?`,
            confirm: () => {
                this.rpc('/web/dataset/call_kw/ks_dashboard_ninja.item/unlink', {
                    model: 'ks_dashboard_ninja.item',
                    method: 'unlink',
                    args: [item.id],
                    kwargs: {}
                }).then(() => {
                    this.notificationService.add('Item deleted successfully', { type: 'success' });
                    this.ks_fetch_items_data();
                }).catch(error => {
                    console.error('Error deleting item:', error);
                    this.notificationService.add('Error deleting item', { type: 'danger' });
                });
            },
            cancel: () => {}
        });
    }

    /**
     * Handle export item data
     */
    onExportItem(ev, itemOrType) {
        ev.stopPropagation();
        
        if (typeof itemOrType === 'string' && itemOrType === 'dashboard') {
            // Export entire dashboard
            const context = {
                ...this.getContext(),
                ks_dashboard_id: this.props.dashboard_id
            };
            
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                res_model: 'ks_dashboard_ninja.board',
                name: 'Export Dashboard',
                views: [[false, 'form']],
                target: 'new',
                context: context
            });
        } else {
            // Export specific item
            const item = itemOrType;
            const context = {
                ...this.getContext(),
                ks_dashboard_id: this.props.dashboard_id,
                ks_item_id: item.id
            };
            
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                res_model: 'ks_dashboard_ninja.item',
                name: 'Export Data',
                views: [[false, 'form']],
                target: 'new',
            context: context,
            flags: { mode: 'readonly' }
        });
    }

    }

    /**
     * Handle fullscreen toggle for item
     */
    onToggleFullscreen(ev, item) {
        if (ev) ev.stopPropagation();
        
        if (item) {
            const itemElement = document.querySelector(`[data-item-id="${item.id}"]`);
            if (itemElement) {
                if (itemElement.classList.contains('ks_fullscreen')) {
                    this.exitFullscreen(itemElement);
                } else {
                    this.enterFullscreen(itemElement);
                }
            }
        } else {
            // Toggle fullscreen for entire dashboard
            const dashboardElement = document.querySelector('.ks_dashboard_ninja_main_container');
            if (dashboardElement) {
                if (dashboardElement.classList.contains('ks_fullscreen')) {
                    this.exitFullscreen(dashboardElement);
                } else {
                    this.enterFullscreen(dashboardElement);
                }
            }
        }
    }

    /**
     * Enter fullscreen mode for item
     */
    enterFullscreen(element) {
        element.classList.add('ks_fullscreen');
        element.style.position = 'fixed';
        element.style.top = '0';
        element.style.left = '0';
        element.style.width = '100vw';
        element.style.height = '100vh';
        element.style.zIndex = '9999';
        element.style.backgroundColor = 'white';
        
        // Add close button
        const closeBtn = document.createElement('button');
        closeBtn.className = 'btn btn-sm btn-outline-secondary ks_fullscreen_close';
        closeBtn.innerHTML = '<i class="fa fa-times"></i>';
        closeBtn.style.position = 'absolute';
        closeBtn.style.top = '10px';
        closeBtn.style.right = '10px';
        closeBtn.onclick = () => this.exitFullscreen(element);
        element.appendChild(closeBtn);
    }

    /**
     * Exit fullscreen mode for item
     */
    exitFullscreen(element) {
        element.classList.remove('ks_fullscreen');
        element.style.position = '';
        element.style.top = '';
        element.style.left = '';
        element.style.width = '';
        element.style.height = '';
        element.style.zIndex = '';
        element.style.backgroundColor = '';
        
        // Remove close button
        const closeBtn = element.querySelector('.ks_fullscreen_close');
        if (closeBtn) {
            closeBtn.remove();
        }
    }

    /**
     * Handle keyboard shortcuts
     */
    onKeyDown(event) {
        // Ctrl/Cmd + E: Toggle edit mode
        if ((event.ctrlKey || event.metaKey) && event.key === 'e') {
            event.preventDefault();
            this.onEditModeToggle();
        }
        
        // Ctrl/Cmd + R: Refresh dashboard
        if ((event.ctrlKey || event.metaKey) && event.key === 'r') {
            event.preventDefault();
            this.onRefreshDashboard();
        }
        
        // Escape: Exit edit mode or fullscreen
        if (event.key === 'Escape') {
            if (this.state.edit_mode) {
                this.onEditModeToggle();
            }
            
            const fullscreenElement = document.querySelector('.ks_fullscreen');
            if (fullscreenElement) {
                this.exitFullscreen(fullscreenElement);
            }
        }
    }

    /**
     * Handle window resize
     */
    onWindowResize() {
        if (this.gridstack) {
            this.gridstack.resize();
        }
        
        // Redraw charts on resize
        this.redrawCharts();
    }

    /**
     * Redraw all charts
     */
    redrawCharts() {
        const chartElements = document.querySelectorAll('.ks_chart_item canvas');
        chartElements.forEach(canvas => {
            const chart = Chart.getChart(canvas);
            if (chart) {
                chart.resize();
            }
        });
    }

    /**
     * Handle list row clicks for drill-down functionality
     */
    onListRowClick(ev, row, item) {
        ev.stopPropagation();
        if (!this.state.edit_mode && item.ks_action) {
            this.actionService.doAction(item.ks_action, {
                additionalContext: {
                    row_data: row,
                    item_id: item.id
                }
            });
        }
    }

    /**
     * Load more data for list pagination
     */
    async loadMoreListData(ev, item, page) {
        ev.stopPropagation();
        try {
            const result = await this.rpc('/web/dataset/call_kw', {
                model: 'ks_dashboard_ninja.item',
                method: 'ks_fetch_list_view_data',
                args: [item.id],
                kwargs: {
                    page: page,
                    limit: item.ks_pagination_limit || 10,
                    context: this.env.context
                }
            });

            if (result) {
                // Update the item data with new page
                const updatedItem = { ...item, ...result };
                this.state.ks_dashboard_data.ks_item_data[item.id] = updatedItem;
                this.render();
            }
        } catch (error) {
            console.error('Error loading list data:', error);
            this.notificationService.add('Error loading list data', { type: 'danger' });
        }
    }

    // Static class properties
    static template = "ks_dashboard_ninja.DashboardTemplate";
    static components = { KsChartComponent };
    static props = {
        dashboard_id: { type: Number, optional: true },
        controller_id: { type: Number, optional: true },
        context: { type: Object, optional: true },
    };
}

// Register the component
registry.category("actions").add("ks_dashboard_ninja", KsDashboardNinja);