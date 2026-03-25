/** @odoo-module **/

// Payroll Dashboard JavaScript
(function() {
    'use strict';

    let monthlyChart = null;

    function formatCurrency(amount) {
        return '₹ ' + amount.toLocaleString('en-IN', { maximumFractionDigits: 2 });
    }

    function updateCards(cards) {
        const elements = {
            'card_total_employees': cards.total_employees,
            'card_active_contracts': cards.active_contracts,
            'card_payslips_this_month': cards.payslips_this_month,
            'card_pending_payslips': cards.pending_payslips,
            'card_total_payroll': formatCurrency(cards.total_payroll_current),
            'card_avg_salary': formatCurrency(cards.avg_salary)
        };

        Object.keys(elements).forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.innerHTML = elements[id];
                el.classList.add('pulse');
                setTimeout(() => el.classList.remove('pulse'), 500);
            }
        });

        const changeEl = document.getElementById('card_payroll_change');
        if (changeEl && cards.payroll_change !== undefined) {
            const change = cards.payroll_change;
            const changeClass = change >= 0 ? 'positive' : 'negative';
            const changeSymbol = change >= 0 ? '↑' : '↓';
            changeEl.innerHTML = `${changeSymbol} ${Math.abs(change).toFixed(1)}% vs last month`;
            changeEl.className = `stat-card-change ${changeClass}`;
        }
    }

    function updateChart(chartData) {
        const ctx = document.getElementById('monthlyChart');
        if (!ctx || typeof Chart === 'undefined') return;

        if (monthlyChart) {
            monthlyChart.destroy();
        }

        const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, 'rgba(102, 126, 234, 0.3)');
        gradient.addColorStop(1, 'rgba(118, 75, 162, 0.1)');

        monthlyChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: chartData.map(d => d.label),
                datasets: [{
                    label: 'Payroll Amount',
                    data: chartData.map(d => d.amount),
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
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 12,
                        titleFont: { size: 14, weight: 'bold' },
                        bodyFont: { size: 13 },
                        borderColor: 'rgb(102, 126, 234)',
                        borderWidth: 1,
                        cornerRadius: 8,
                        displayColors: false,
                        callbacks: {
                            label: function(context) {
                                return 'Amount: ' + formatCurrency(context.parsed.y);
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { font: { size: 12, weight: '600' }, color: '#64748b' }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(0, 0, 0, 0.05)', drawBorder: false },
                        ticks: {
                            font: { size: 12, weight: '600' },
                            color: '#64748b',
                            callback: function(value) {
                                if (value >= 100000) {
                                    return '₹' + (value / 100000).toFixed(1) + 'L';
                                } else if (value >= 1000) {
                                    return '₹' + (value / 1000).toFixed(0) + 'K';
                                }
                                return '₹' + value;
                            }
                        }
                    }
                }
            }
        });
    }

    function updateTopEarners(earners) {
        const container = document.getElementById('top_earners_list');
        if (!container) return;

        if (earners.length === 0) {
            container.innerHTML = '<div style="text-align: center; padding: 40px; color: #64748b;">No data available</div>';
            return;
        }

        let html = '';
        earners.forEach((emp, index) => {
            const rankClass = index === 0 ? 'rank-1' : index === 1 ? 'rank-2' : index === 2 ? 'rank-3' : 'rank-other';
            html += `
                <div class="employee-item">
                    <div style="display: flex; align-items: center; flex: 1;">
                        <div class="employee-rank ${rankClass}">${index + 1}</div>
                        <div class="employee-name">${emp.name}</div>
                    </div>
                    <div class="employee-amount">${formatCurrency(emp.amount)}</div>
                </div>
            `;
        });
        container.innerHTML = html;
    }

    function getSelectedPeriod() {
        const select = document.getElementById('monthly_period_filter');
        if (!select) return 6;
        const value = parseInt(select.value, 10);
        return isNaN(value) || value <= 0 ? 6 : value;
    }

    function loadDashboardData() {
        if (!window.location.pathname.includes('/payroll/dashboard')) {
            return;
        }

        const loadingElements = document.querySelectorAll('.stat-card-value, .stat-box-value');
        loadingElements.forEach(el => {
            if (!el.innerHTML || el.innerHTML.trim() === '' || el.innerHTML.includes('loading-spinner')) {
                el.innerHTML = '<span class="loading-spinner" style="width: 16px; height: 16px; border-width: 2px;"></span>';
            }
        });

        const period = getSelectedPeriod();
        const url = `/payroll/dashboard/data?period=${encodeURIComponent(period)}`;

        fetch(url, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
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
            if (!data) throw new Error('No data received');
            if (data.cards) updateCards(data.cards);
            if (data.monthly_chart && data.monthly_chart.length > 0) {
                updateChart(data.monthly_chart);
            } else if (data.monthly_chart) {
                updateChart(data.monthly_chart);
            }
            if (data.top_earners) updateTopEarners(data.top_earners);
        })
        .catch(error => {
            console.error('Error loading dashboard:', error);
            const errorMsg = '<span style="color: #f5576c; font-size: 14px;">Error</span>';
            document.querySelectorAll('.stat-card-value, .stat-box-value').forEach(el => {
                el.innerHTML = errorMsg;
            });
            const container = document.getElementById('top_earners_list');
            if (container) {
                container.innerHTML = '<div style="text-align: center; padding: 40px; color: #f5576c;">Error loading data. Please refresh the page.</div>';
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadDashboardData);
    } else {
        loadDashboardData();
    }

    document.addEventListener('change', (ev) => {
        if (ev.target && ev.target.id === 'monthly_period_filter') {
            loadDashboardData();
        }
    });

    setTimeout(loadDashboardData, 500);
})();