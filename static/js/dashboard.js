/**
 * NEXUS Engine V10 — Dashboard JavaScript
 * ========================================
 * Real-time updates via Socket.IO
 */

class NexusDashboard {
    constructor() {
        this.socket = null;
        this.connected = false;
        this.init();
    }

    init() {
        this.initSocket();
        this.initEventListeners();
        this.loadInitialData();
    }

    // Socket.IO connection
    initSocket() {
        this.socket = io();

        this.socket.on('connect', () => {
            console.log('✅ Connected to NEXUS Engine');
            this.connected = true;
            this.updateConnectionStatus(true);
        });

        this.socket.on('disconnect', () => {
            console.log('❌ Disconnected from NEXUS Engine');
            this.connected = false;
            this.updateConnectionStatus(false);
        });

        // Real-time updates
        this.socket.on('positions_update', (data) => {
            this.updatePositions(data.positions);
        });

        this.socket.on('balance_update', (data) => {
            this.updateBalance(data.balance);
        });

        this.socket.on('pnl_update', (data) => {
            this.updatePnL(data);
        });

        this.socket.on('agent_health', (data) => {
            this.updateAgentHealth(data);
        });

        this.socket.on('trade_notification', (data) => {
            this.showNotification(data);
        });
    }

    // Event listeners
    initEventListeners() {
        // Bot control buttons
        document.querySelectorAll('[data-action]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.target.dataset.action;
                this.handleAction(action);
            });
        });

        // Refresh buttons
        document.querySelectorAll('[data-refresh]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const target = e.target.dataset.refresh;
                this.refreshData(target);
            });
        });
    }

    // Load initial data
    async loadInitialData() {
        await Promise.all([
            this.loadPositions(),
            this.loadBalance(),
            this.loadSettings(),
            this.loadAgentStatus(),
        ]);
    }

    // API calls
    async apiCall(endpoint, method = 'GET', body = null) {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
        };

        if (body) {
            options.body = JSON.stringify(body);
        }

        try {
            const response = await fetch(endpoint, options);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Request failed');
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            this.showError(error.message);
            return null;
        }
    }

    // Load positions
    async loadPositions() {
        const data = await this.apiCall('/api/trading/positions');
        if (data) {
            this.updatePositions(data.positions);
        }
    }

    // Load balance
    async loadBalance() {
        const data = await this.apiCall('/api/trading/balance');
        if (data) {
            this.updateBalance(data.balance);
        }
    }

    // Load settings
    async loadSettings() {
        const data = await this.apiCall('/api/trading/settings');
        if (data) {
            this.updateSettings(data);
        }
    }

    // Load agent status
    async loadAgentStatus() {
        const data = await this.apiCall('/api/admin/health/agents');
        if (data) {
            this.updateAgentHealth(data.agents);
        }
    }

    // Handle actions
    async handleAction(action) {
        switch (action) {
            case 'start-bot':
                await this.apiCall('/api/trading/bot/start', 'POST');
                this.showNotification({message: 'Bot started', type: 'success'});
                break;
            case 'stop-bot':
                await this.apiCall('/api/trading/bot/stop', 'POST');
                this.showNotification({message: 'Bot stopped', type: 'info'});
                break;
            case 'refresh-all':
                await this.loadInitialData();
                this.showNotification({message: 'Data refreshed', type: 'success'});
                break;
            default:
                console.log('Unknown action:', action);
        }
    }

    // Refresh specific data
    async refreshData(target) {
        switch (target) {
            case 'positions':
                await this.loadPositions();
                break;
            case 'balance':
                await this.loadBalance();
                break;
            case 'settings':
                await this.loadSettings();
                break;
        }
    }

    // Update UI methods
    updatePositions(positions) {
        const container = document.getElementById('positions-table');
        if (!container) return;

        if (!positions || positions.length === 0) {
            container.innerHTML = '<tr><td colspan="6" class="text-center">No open positions</td></tr>';
            return;
        }

        container.innerHTML = positions.map(pos => `
            <tr>
                <td>${pos.symbol}</td>
                <td><span class="badge badge-${pos.side.toLowerCase()}">${pos.side}</span></td>
                <td>${pos.size}</td>
                <td>$${pos.entry_price.toFixed(2)}</td>
                <td class="${pos.unrealized_pnl >= 0 ? 'positive' : 'negative'}">
                    ${pos.unrealized_pnl >= 0 ? '+' : ''}$${pos.unrealized_pnl.toFixed(2)}
                </td>
                <td><span class="badge badge-${pos.status.toLowerCase()}">${pos.status}</span></td>
            </tr>
        `).join('');
    }

    updateBalance(balance) {
        const container = document.getElementById('balance-display');
        if (!container) return;

        const usdt = balance.USDT || 0;
        container.innerHTML = `
            <div class="stat-value">$${usdt.toLocaleString('en-US', {minimumFractionDigits: 2})}</div>
            <div class="stat-label">USDT Balance</div>
        `;
    }

    updatePnL(data) {
        const container = document.getElementById('pnl-display');
        if (!container) return;

        const pnl = data.daily_pnl || 0;
        const isPositive = pnl >= 0;

        container.innerHTML = `
            <div class="stat-value ${isPositive ? 'positive' : 'negative'}">
                ${isPositive ? '+' : ''}$${pnl.toFixed(2)}
            </div>
            <div class="stat-label">Daily PnL</div>
        `;
    }

    updateAgentHealth(agents) {
        const container = document.getElementById('agent-health');
        if (!container) return;

        container.innerHTML = Object.entries(agents).map(([name, health]) => `
            <div class="agent-status ${health.healthy ? 'online' : 'offline'}">
                <span class="status-dot ${health.healthy ? 'online' : 'offline'}"></span>
                <span>${name}</span>
                <span class="agent-run-count">${health.run_count} runs</span>
            </div>
        `).join('');
    }

    updateSettings(settings) {
        const container = document.getElementById('settings-display');
        if (!container) return;

        container.innerHTML = `
            <div class="setting-item">
                <span class="setting-label">Strategy:</span>
                <span class="setting-value">${settings.strategy}</span>
            </div>
            <div class="setting-item">
                <span class="setting-label">Symbols:</span>
                <span class="setting-value">${settings.symbols.join(', ')}</span>
            </div>
            <div class="setting-item">
                <span class="setting-label">Timeframe:</span>
                <span class="setting-value">${settings.timeframe}</span>
            </div>
            <div class="setting-item">
                <span class="setting-label">Confidence:</span>
                <span class="setting-value">${settings.confidence_threshold}%</span>
            </div>
        `;
    }

    updateConnectionStatus(connected) {
        const indicator = document.getElementById('connection-status');
        if (!indicator) return;

        indicator.innerHTML = connected 
            ? '<span class="status-dot online"></span> Connected'
            : '<span class="status-dot offline"></span> Disconnected';
    }

    // Notifications
    showNotification(data) {
        const container = document.getElementById('notifications');
        if (!container) return;

        const notification = document.createElement('div');
        notification.className = `notification notification-${data.type || 'info'}`;
        notification.innerHTML = `
            <span class="notification-message">${data.message}</span>
            <button class="notification-close">&times;</button>
        `;

        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.remove();
        });

        container.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    showError(message) {
        this.showNotification({message, type: 'error'});
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.nexusDashboard = new NexusDashboard();
});
