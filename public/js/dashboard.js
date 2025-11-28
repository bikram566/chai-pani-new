let refreshInterval;

document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    loadDashboardData();

    // Auto-refresh every 30 seconds
    refreshInterval = setInterval(loadDashboardData, 30000);
});

async function loadDashboardData() {
    try {
        // Show loading indicator
        updateRefreshStatus('Refreshing...');

        const token = localStorage.getItem('token');
        const headers = {
            'Authorization': `Bearer ${token}`
        };

        // Fetch Stats
        const statsResponse = await fetch('/api/sales/stats', { headers });
        if (!statsResponse.ok) throw new Error('Failed to fetch stats');
        const stats = await statsResponse.json();

        document.getElementById('todayRevenue').textContent = formatCurrency(stats.today);
        document.getElementById('todayOrders').textContent = stats.total_orders_today;
        document.getElementById('weekRevenue').textContent = formatCurrency(stats.week);
        document.getElementById('monthRevenue').textContent = formatCurrency(stats.month);

        // Fetch Top Items
        const itemsResponse = await fetch('/api/sales/top-items', { headers });
        if (!itemsResponse.ok) throw new Error('Failed to fetch top items');
        const topItems = await itemsResponse.json();

        renderTopItems(topItems);

        // Update last refresh time
        const now = new Date();
        const timeStr = now.toLocaleTimeString();
        updateRefreshStatus(`Last updated: ${timeStr}`);
    } catch (error) {
        console.error('Error loading dashboard:', error);
        updateRefreshStatus('Error loading data');
    }
}

function updateRefreshStatus(message) {
    const statusEl = document.getElementById('refreshStatus');
    if (statusEl) {
        statusEl.textContent = message;
    }
}

function renderTopItems(items) {
    const container = document.getElementById('topItemsList');
    container.innerHTML = '';

    if (items.length === 0) {
        container.innerHTML = '<p>No sales data available yet.</p>';
        return;
    }

    items.forEach((item, index) => {
        const row = document.createElement('div');
        row.className = 'top-item-row';
        row.innerHTML = `
            <div>
                <span class="item-rank">#${index + 1}</span>
                <span class="item-name">${item.name}</span>
            </div>
            <span class="item-quantity">${item.quantity} sold</span>
        `;
        container.appendChild(row);
    });
}

function formatCurrency(amount) {
    return '₹' + parseFloat(amount).toFixed(2);
}

async function downloadDailyReport() {
    try {
        updateRefreshStatus('Preparing download...');

        const token = localStorage.getItem('token');
        if (!token) {
            alert('Please log in first');
            return;
        }

        const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD format

        console.log('Fetching report for date:', today);

        const response = await fetch(`/api/sales/daily-report?date=${today}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        console.log('Response status:', response.status);

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Download failed:', errorText);
            throw new Error(`Failed to download report: ${response.status}`);
        }

        // Get the CSV blob
        const blob = await response.blob();
        console.log('Received blob, size:', blob.size);

        if (blob.size === 0) {
            throw new Error('Received empty file');
        }

        // Create a download link and trigger it
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `sales_report_${today}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        console.log('Download triggered successfully');
        updateRefreshStatus('Report downloaded successfully!');
        setTimeout(() => {
            const now = new Date();
            const timeStr = now.toLocaleTimeString();
            updateRefreshStatus(`Last updated: ${timeStr}`);
        }, 3000);
    } catch (error) {
        console.error('Error downloading report:', error);
        updateRefreshStatus('Download failed - check console');
        alert(`Failed to download sales report: ${error.message}\n\nPlease check the browser console for details.`);
    }
}

// Make download function globally accessible
window.downloadDailyReport = downloadDailyReport;

// Make refresh function globally accessible for manual refresh button
window.refreshDashboard = loadDashboardData;
