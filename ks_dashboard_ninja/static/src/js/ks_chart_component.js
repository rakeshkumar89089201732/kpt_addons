/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

// Chart.js imports
import Chart from 'chart.js/auto';
import ChartDataLabels from 'chartjs-plugin-datalabels';

export class KsChartComponent extends Component {
    static template = `
        <div class="ks_chart_container h-100">
            <div class="ks_chart_content h-100 position-relative">
                <canvas t-ref="chartCanvas" class="ks_chart_canvas w-100 h-100"/>
                <div class="ks_chart_loading position-absolute top-50 start-50 translate-middle" 
                     t-if="state.loading">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
                <div class="ks_chart_error text-center text-danger p-3" 
                     t-if="state.error">
                    <i class="fa fa-exclamation-triangle fa-2x mb-2"/>
                    <p t-esc="state.error"/>
                </div>
            </div>
        </div>
    `;
    static props = {
        item: Object,
        chartData: Object,
        chartType: String,
        editMode: { type: Boolean, optional: true },
        onChartClick: { type: Function, optional: true },
    };

    setup() {
        this.chartRef = useRef("chartCanvas");
        this.chart = null;
        this.state = useState({
            loading: false,
            error: null,
        });

        // Chart configuration
        this.chartColors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
            '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF6384'
        ];

        this.defaultChartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 20,
                        generateLabels: (chart) => this.generateLegendLabels(chart),
                    }
                },
                tooltip: {
                    enabled: true,
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: (context) => this.formatTooltipLabel(context),
                    }
                },
                datalabels: {
                    display: false, // Will be enabled based on item configuration
                }
            },
            scales: {},
            onClick: (event, elements) => {
                if (this.props.onChartClick && elements.length > 0) {
                    this.props.onChartClick(event, elements, this.props.item);
                }
            }
        };

        onMounted(() => {
            this.renderChart();
        });

        onWillUnmount(() => {
            this.destroyChart();
        });
    }

    /**
     * Render the chart based on chart type and data
     */
    renderChart() {
        if (!this.chartRef.el || !this.props.chartData) {
            return;
        }

        this.destroyChart();

        try {
            const ctx = this.chartRef.el.getContext('2d');
            const chartConfig = this.buildChartConfig();
            
            this.chart = new Chart(ctx, chartConfig);
        } catch (error) {
            console.error('Error rendering chart:', error);
            this.state.error = _t("Failed to render chart");
        }
    }

    /**
     * Build chart configuration based on chart type and data
     */
    buildChartConfig() {
        const chartType = this.getChartJsType();
        const options = this.buildChartOptions();
        const data = this.processChartData();

        return {
            type: chartType,
            data: data,
            options: options,
            plugins: this.getChartPlugins(),
        };
    }

    /**
     * Convert dashboard chart type to Chart.js type
     */
    getChartJsType() {
        const typeMapping = {
            'ks_bar_chart': 'bar',
            'ks_horizontalBar_chart': 'bar',
            'ks_line_chart': 'line',
            'ks_area_chart': 'line',
            'ks_pie_chart': 'pie',
            'ks_doughnut_chart': 'doughnut',
            'ks_polarArea_chart': 'polarArea',
            'ks_scatter_chart': 'scatter',
            'ks_bubble_chart': 'bubble',
        };

        return typeMapping[this.props.chartType] || 'bar';
    }

    /**
     * Process chart data for Chart.js format
     */
    processChartData() {
        const chartData = this.props.chartData;
        
        if (!chartData || !chartData.datasets) {
            return { labels: [], datasets: [] };
        }

        // Process datasets
        const datasets = chartData.datasets.map((dataset, index) => {
            const processedDataset = {
                label: dataset.label || '',
                data: dataset.data || [],
                backgroundColor: this.getDatasetColors(dataset, index, 'background'),
                borderColor: this.getDatasetColors(dataset, index, 'border'),
                borderWidth: dataset.borderWidth || 1,
            };

            // Chart type specific configurations
            const chartType = this.getChartJsType();
            
            if (chartType === 'line' || this.props.chartType === 'ks_area_chart') {
                processedDataset.fill = this.props.chartType === 'ks_area_chart';
                processedDataset.tension = 0.4;
            }

            if (this.props.chartType === 'ks_horizontalBar_chart') {
                processedDataset.indexAxis = 'y';
            }

            // Handle cumulative data if configured
            if (this.props.item.ks_chart_cumulative_field && dataset.ks_chart_cumulative_field) {
                const cumulativeData = this.calculateCumulativeData(dataset.data);
                datasets.push({
                    ...processedDataset,
                    label: 'Cumulative ' + processedDataset.label,
                    data: cumulativeData,
                    type: 'line',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    borderColor: 'rgba(255, 99, 132, 1)',
                });
            }

            return processedDataset;
        });

        return {
            labels: chartData.labels || [],
            datasets: datasets,
        };
    }

    /**
     * Get colors for dataset
     */
    getDatasetColors(dataset, index, type) {
        if (dataset.backgroundColor && type === 'background') {
            return dataset.backgroundColor;
        }
        if (dataset.borderColor && type === 'border') {
            return dataset.borderColor;
        }

        // Use default colors
        const baseColor = this.chartColors[index % this.chartColors.length];
        
        if (type === 'background') {
            return this.isCircularChart() ? 
                this.generateCircularColors(dataset.data.length) : 
                this.hexToRgba(baseColor, 0.6);
        } else {
            return this.isCircularChart() ? 
                this.generateCircularColors(dataset.data.length, 1) : 
                baseColor;
        }
    }

    /**
     * Generate colors for circular charts (pie, doughnut, polar)
     */
    generateCircularColors(count, alpha = 0.8) {
        const colors = [];
        for (let i = 0; i < count; i++) {
            const color = this.chartColors[i % this.chartColors.length];
            colors.push(alpha < 1 ? this.hexToRgba(color, alpha) : color);
        }
        return colors;
    }

    /**
     * Convert hex color to rgba
     */
    hexToRgba(hex, alpha) {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }

    /**
     * Check if chart is circular type
     */
    isCircularChart() {
        const circularTypes = ['ks_pie_chart', 'ks_doughnut_chart', 'ks_polarArea_chart'];
        return circularTypes.includes(this.props.chartType);
    }

    /**
     * Calculate cumulative data
     */
    calculateCumulativeData(data) {
        let cumulative = 0;
        return data.map(value => {
            cumulative += value;
            return cumulative;
        });
    }

    /**
     * Build chart options
     */
    buildChartOptions() {
        const options = JSON.parse(JSON.stringify(this.defaultChartOptions));
        const chartType = this.getChartJsType();

        // Configure scales for non-circular charts
        if (!this.isCircularChart()) {
            options.scales = this.buildScalesConfig();
        }

        // Configure horizontal bar chart
        if (this.props.chartType === 'ks_horizontalBar_chart') {
            options.indexAxis = 'y';
        }

        // Configure data labels
        if (this.props.item.ks_show_data_value) {
            options.plugins.datalabels.display = true;
            options.plugins.datalabels.formatter = (value, context) => {
                return this.formatDataLabel(value, context);
            };
        }

        // Configure legend
        if (this.props.item.ks_hide_legend) {
            options.plugins.legend.display = false;
        }

        return options;
    }

    /**
     * Build scales configuration
     */
    buildScalesConfig() {
        const scales = {};

        // Y-axis configuration
        scales.y = {
            beginAtZero: true,
            ticks: {
                callback: (value) => this.formatAxisLabel(value),
            }
        };

        // X-axis configuration
        scales.x = {
            ticks: {
                maxRotation: 45,
                minRotation: 0,
            }
        };

        // Handle dual axis for bar charts with multiple measures
        if (this.props.item.ks_chart_measure_field_2 && this.props.chartType === 'ks_bar_chart') {
            scales.y1 = {
                type: 'linear',
                display: true,
                position: 'right',
                beginAtZero: true,
                ticks: {
                    callback: (value) => this.formatAxisLabel(value),
                },
                grid: {
                    drawOnChartArea: false,
                },
            };
        }

        return scales;
    }

    /**
     * Get chart plugins
     */
    getChartPlugins() {
        const plugins = [];

        // Add data labels plugin if needed
        if (this.props.item.ks_show_data_value) {
            plugins.push(ChartDataLabels);
        }

        // Add no data plugin
        plugins.push({
            id: 'noDataPlugin',
            afterDraw: (chart) => {
                if (chart.data.labels.length === 0) {
                    const ctx = chart.ctx;
                    const width = chart.width;
                    const height = chart.height;
                    
                    chart.clear();
                    ctx.save();
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.font = '16px Arial';
                    ctx.fillStyle = '#999';
                    ctx.fillText(_t('No data available'), width / 2, height / 2);
                    ctx.restore();
                }
            }
        });

        return plugins;
    }

    /**
     * Format tooltip label
     */
    formatTooltipLabel(context) {
        let label = context.dataset.label || '';
        if (label) {
            label += ': ';
        }
        
        const value = context.parsed.y !== undefined ? context.parsed.y : context.parsed;
        label += this.formatValue(value);
        
        return label;
    }

    /**
     * Format data label
     */
    formatDataLabel(value, context) {
        return this.formatValue(value);
    }

    /**
     * Format axis label
     */
    formatAxisLabel(value) {
        return this.formatValue(value);
    }

    /**
     * Format value based on item configuration
     */
    formatValue(value) {
        if (typeof value !== 'number') {
            return value;
        }

        // Apply number formatting based on item configuration
        if (this.props.item.ks_data_format) {
            return this.formatNumber(value, this.props.item.ks_data_format, this.props.item.ks_precision_digits);
        }

        return value.toLocaleString();
    }

    /**
     * Format number with specific format
     */
    formatNumber(value, format, precision = 2) {
        switch (format) {
            case 'global':
                return this.globalNumberFormat(value);
            case 'indian':
                return this.indianNumberFormat(value);
            case 'exact':
                return value.toFixed(precision);
            default:
                return value.toLocaleString();
        }
    }

    /**
     * Global number formatting (K, M, B)
     */
    globalNumberFormat(value) {
        if (Math.abs(value) >= 1e9) {
            return (value / 1e9).toFixed(1) + 'B';
        } else if (Math.abs(value) >= 1e6) {
            return (value / 1e6).toFixed(1) + 'M';
        } else if (Math.abs(value) >= 1e3) {
            return (value / 1e3).toFixed(1) + 'K';
        }
        return value.toString();
    }

    /**
     * Indian number formatting (K, L, Cr)
     */
    indianNumberFormat(value) {
        if (Math.abs(value) >= 1e7) {
            return (value / 1e7).toFixed(1) + 'Cr';
        } else if (Math.abs(value) >= 1e5) {
            return (value / 1e5).toFixed(1) + 'L';
        } else if (Math.abs(value) >= 1e3) {
            return (value / 1e3).toFixed(1) + 'K';
        }
        return value.toString();
    }

    /**
     * Generate legend labels
     */
    generateLegendLabels(chart) {
        const original = Chart.defaults.plugins.legend.labels.generateLabels;
        const labels = original.call(this, chart);
        
        // Truncate long labels
        labels.forEach(label => {
            if (label.text && label.text.length > 25) {
                label.text = label.text.substring(0, 22) + '...';
            }
        });
        
        return labels;
    }

    /**
     * Destroy existing chart
     */
    destroyChart() {
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }
    }

    /**
     * Update chart data
     */
    updateChart(newData) {
        if (this.chart && newData) {
            this.chart.data = this.processChartData();
            this.chart.update();
        } else {
            this.renderChart();
        }
    }
}