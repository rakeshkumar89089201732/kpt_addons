/** @odoo-module **/

// Modern Attendance Dashboard JavaScript
(function() {
    'use strict';

    let dailyChart = null;

    function updateCards(cards) {
        const elements = {
            'card_total_employees': cards.total_employees,
            'card_today_checkins': cards.today_checkins,
            'card_at_work': cards.at_work,
            'card_week_hours': cards.week_hours + 'h',
            'card_month_hours': cards.month_hours + 'h',
            'card_month_overtime': cards.month_overtime + 'h'
        };

        Object.keys(elements).forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.innerHTML = elements[id];
                el.classList.add('pulse');
                setTimeout(() => el.classList.remove('pulse'), 500);
            }
        });
    }

    function updateChart(chartData) {
        const ctx = document.getElementById('dailyChart');
        if (!ctx || typeof Chart === 'undefined') return;

        if (dailyChart) {
            dailyChart.destroy();
        }

        const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, 'rgba(102, 126, 234, 0.3)');
        gradient.addColorStop(1, 'rgba(118, 75, 162, 0.1)');

        dailyChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: chartData.map(d => d.label),
                datasets: [{
                    label: 'Hours Worked',
                    data: chartData.map(d => d.hours),
                    borderColor: 'rgb(102, 126, 234)',
                    backgroundColor: gradient,
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    pointBackgroundColor: 'rgb(102, 126, 234)',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 12,
                        titleFont: {
                            size: 14,
                            weight: 'bold'
                        },
                        bodyFont: {
                            size: 13
                        },
                        borderColor: 'rgb(102, 126, 234)',
                        borderWidth: 1,
                        cornerRadius: 8,
                        displayColors: false,
                        callbacks: {
                            label: function(context) {
                                return 'Hours: ' + context.parsed.y.toFixed(1) + 'h';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            font: {
                                size: 12,
                                weight: '600'
                            },
                            color: '#64748b'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)',
                            drawBorder: false
                        },
                        ticks: {
                            font: {
                                size: 12,
                                weight: '600'
                            },
                            color: '#64748b',
                            callback: function(value) {
                                return value + 'h';
                            }
                        }
                    }
                }
            }
        });
    }

    function updateTopEmployees(employees) {
        const container = document.getElementById('top_employees_list');
        if (!container) return;

        if (employees.length === 0) {
            container.innerHTML = '<div style="text-align: center; padding: 40px; color: #64748b;">No data available</div>';
            return;
        }

        let html = '';
        employees.forEach((emp, index) => {
            const rankClass = index === 0 ? 'rank-1' : index === 1 ? 'rank-2' : index === 2 ? 'rank-3' : 'rank-other';
            html += `
                <div class="employee-item">
                    <div style="display: flex; align-items: center; flex: 1;">
                        <div class="employee-rank ${rankClass}">${index + 1}</div>
                        <div class="employee-name">${emp.name}</div>
                    </div>
                    <div class="employee-hours">${emp.hours.toFixed(1)}h</div>
                </div>
            `;
        });
        container.innerHTML = html;
    }

    function getSelectedPeriod() {
        const select = document.getElementById('daily_period_filter');
        if (!select) {
            return 7;
        }
        const value = parseInt(select.value, 10);
        if (isNaN(value) || value <= 0) {
            return 7;
        }
        return value;
    }

    function loadDashboardData() {
        if (!window.location.pathname.includes('/attendance/dashboard')) {
            return;
        }

        // Show loading state
        const loadingElements = document.querySelectorAll('.stat-card-value, .stat-box-value');
        loadingElements.forEach(el => {
            if (!el.innerHTML || el.innerHTML.trim() === '' || el.innerHTML.includes('loading-spinner')) {
                el.innerHTML = '<span class="loading-spinner" style="width: 16px; height: 16px; border-width: 2px;"></span>';
            }
        });

        const period = getSelectedPeriod();

        // Fetch data - simple GET request with period filter
        const url = `/attendance/dashboard/data?period=${encodeURIComponent(period)}`;

        fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
        })
        .then(response => {
            if (!response.ok) {
                return response.text().then(text => {
                    throw new Error('HTTP ' + response.status + ': ' + text.substring(0, 100));
                });
            }
            return response.json();
        })
        .then(data => {
            console.log('Dashboard data received:', data);
            if (!data) {
                throw new Error('No data received');
            }
            if (data.cards) {
                updateCards(data.cards);
            }
            if (data.daily_chart && data.daily_chart.length > 0) {
                updateChart(data.daily_chart);
            } else if (data.daily_chart) {
                // Even if empty, try to render chart
                updateChart(data.daily_chart);
            }
            if (data.top_employees) {
                updateTopEmployees(data.top_employees);
            }
        })
        .catch(error => {
            console.error('Error loading dashboard:', error);
            // Show error state
            const errorMsg = '<span style="color: #f5576c; font-size: 14px;">Error</span>';
            document.querySelectorAll('.stat-card-value, .stat-box-value').forEach(el => {
                el.innerHTML = errorMsg;
            });
            const container = document.getElementById('top_employees_list');
            if (container) {
                container.innerHTML = '<div style="text-align: center; padding: 40px; color: #f5576c;">Error loading data. Please refresh the page.</div>';
            }
        });
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadDashboardData);
    } else {
        loadDashboardData();
    }

    // Re-load data when period filter changes
    document.addEventListener('change', (ev) => {
        if (ev.target && ev.target.id === 'daily_period_filter') {
            loadDashboardData();
        }
    });

    // Also try after a short delay in case Chart.js loads later
    setTimeout(loadDashboardData, 500);
})();
