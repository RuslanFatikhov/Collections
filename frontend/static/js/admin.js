class AdminPanel {
    constructor() {
        this.currentTab = 'dashboard';
        this.currentUsersPage = 1;
        this.currentCollectionsPage = 1;
        this.usersPerPage = 20;
        this.collectionsPerPage = 20;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadStats();
    }

    bindEvents() {
        // Tab navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Users search
        document.getElementById('users-search-btn').addEventListener('click', () => {
            this.searchUsers();
        });

        document.getElementById('users-search').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.searchUsers();
            }
        });

        // Collections search
        document.getElementById('collections-search-btn').addEventListener('click', () => {
            this.searchCollections();
        });

        document.getElementById('collections-search').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.searchCollections();
            }
        });

        // Modal events
        document.getElementById('confirm-cancel').addEventListener('click', () => {
            this.hideModal();
        });

        document.getElementById('confirm-ok').addEventListener('click', () => {
            this.executeConfirmedAction();
        });
    }

    switchTab(tabName) {
        // Update nav buttons
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update tab content
        document.querySelectorAll('.admin-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');

        this.currentTab = tabName;

        // Load data for the tab
        switch (tabName) {
            case 'dashboard':
                this.loadStats();
                break;
            case 'users':
                this.loadUsers();
                break;
            case 'collections':
                this.loadCollections();
                break;
        }
    }

    async loadStats() {
        try {
            this.showLoading();
            const response = await api.get('/api/admin/stats');
            const stats = response.data;

            document.getElementById('total-users').textContent = stats.total_users;
            document.getElementById('active-users').textContent = stats.active_users;
            document.getElementById('blocked-users').textContent = stats.blocked_users;
            document.getElementById('total-collections').textContent = stats.total_collections;
            document.getElementById('active-collections').textContent = stats.active_collections;
            document.getElementById('blocked-collections').textContent = stats.blocked_collections;
            document.getElementById('new-users-month').textContent = stats.new_users_month;
            document.getElementById('new-collections-month').textContent = stats.new_collections_month;
        } catch (error) {
            console.error('Error loading stats:', error);
            this.showError('Failed to load statistics');
        } finally {
            this.hideLoading();
        }
    }

    async loadUsers(page = 1, search = '') {
        try {
            this.showLoading();
            const params = new URLSearchParams({
                page: page,
                per_page: this.usersPerPage
            });
            
            if (search) {
                params.append('search', search);
            }

            const response = await api.get(`/api/admin/users?${params}`);
            const data = response.data;

            this.renderUsersTable(data.users);
            this.renderUsersPagination(data);
            this.currentUsersPage = page;
        } catch (error) {
            console.error('Error loading users:', error);
            this.showError('Failed to load users');
        } finally {
            this.hideLoading();
        }
    }

    async loadCollections(page = 1, search = '') {
        try {
            this.showLoading();
            const params = new URLSearchParams({
                page: page,
                per_page: this.collectionsPerPage
            });
            
            if (search) {
                params.append('search', search);
            }

            const response = await api.get(`/api/admin/collections?${params}`);
            const data = response.data;

            this.renderCollectionsTable(data.collections);
            this.renderCollectionsPagination(data);
            this.currentCollectionsPage = page;
        } catch (error) {
            console.error('Error loading collections:', error);
            this.showError('Failed to load collections');
        } finally {
            this.hideLoading();
        }
    }

    renderUsersTable(users) {
        const tbody = document.getElementById('users-tbody');
        tbody.innerHTML = '';

        users.forEach(user => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${user.id}</td>
                <td>
                    <div class="user-info">
                        ${user.avatar_url ? `<img src="${user.avatar_url}" alt="Avatar" class="user-avatar">` : ''}
                        <span>${user.name}</span>
                    </div>
                </td>
                <td>${user.email}</td>
                <td>${user.collections_count || 0}</td>
                <td>${this.formatDate(user.created_at)}</td>
                <td>
                    <span class="status ${user.is_blocked ? 'blocked' : 'active'}">
                        ${user.is_blocked ? 'Blocked' : 'Active'}
                    </span>
                </td>
                <td>
                    <div class="action-buttons">
                        ${user.is_blocked ? 
                            `<button class="btn-success" onclick="adminPanel.confirmAction('unblock-user', ${user.id}, '${user.name}')">Unblock</button>` :
                            `<button class="btn-danger" onclick="adminPanel.confirmAction('block-user', ${user.id}, '${user.name}')">Block</button>`
                        }
                    </div>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    renderCollectionsTable(collections) {
        const tbody = document.getElementById('collections-tbody');
        tbody.innerHTML = '';

        collections.forEach(collection => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${collection.id}</td>
                <td>
                    <div class="collection-info">
                        ${collection.cover_url ? `<img src="${collection.cover_url}" alt="Cover" class="collection-cover">` : ''}
                        <span>${collection.name}</span>
                    </div>
                </td>
                <td>
                    <span class="user-link" data-user-id="${collection.user.id}">
                        ${collection.user.name}
                    </span>
                </td>
                <td>${collection.items_count || 0}</td>
                <td>
                    <span class="status ${collection.is_public ? 'public' : 'private'}">
                        ${collection.is_public ? 'Public' : 'Private'}
                    </span>
                </td>
                <td>${this.formatDate(collection.created_at)}</td>
                <td>
                    <span class="status ${collection.is_blocked ? 'blocked' : 'active'}">
                        ${collection.is_blocked ? 'Blocked' : 'Active'}
                    </span>
                </td>
                <td>
                    <div class="action-buttons">
                        ${collection.is_blocked ? 
                            `<button class="btn-success" onclick="adminPanel.confirmAction('unblock-collection', ${collection.id}, '${collection.name}')">Unblock</button>` :
                            `<button class="btn-danger" onclick="adminPanel.confirmAction('block-collection', ${collection.id}, '${collection.name}')">Block</button>`
                        }
                        <a href="/collection/${collection.id}" target="_blank" class="btn-secondary">View</a>
                    </div>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    renderUsersPagination(data) {
        const pagination = document.getElementById('users-pagination');
        this.renderPagination(pagination, data, (page) => {
            const search = document.getElementById('users-search').value;
            this.loadUsers(page, search);
        });
    }

    renderCollectionsPagination(data) {
        const pagination = document.getElementById('collections-pagination');
        this.renderPagination(pagination, data, (page) => {
            const search = document.getElementById('collections-search').value;
            this.loadCollections(page, search);
        });
    }

    renderPagination(container, data, onPageClick) {
        container.innerHTML = '';

        if (data.pages <= 1) return;

        const createPageButton = (page, text = page, isActive = false, isDisabled = false) => {
            const button = document.createElement('button');
            button.textContent = text;
            button.className = `page-btn ${isActive ? 'active' : ''} ${isDisabled ? 'disabled' : ''}`;
            if (!isDisabled) {
                button.addEventListener('click', () => onPageClick(page));
            }
            return button;
        };

        // Previous button
        if (data.current_page > 1) {
            container.appendChild(createPageButton(data.current_page - 1, '‹'));
        }

        // Page numbers
        const startPage = Math.max(1, data.current_page - 2);
        const endPage = Math.min(data.pages, data.current_page + 2);

        if (startPage > 1) {
            container.appendChild(createPageButton(1));
            if (startPage > 2) {
                const span = document.createElement('span');
                span.textContent = '...';
                span.className = 'page-dots';
                container.appendChild(span);
            }
        }

        for (let i = startPage; i <= endPage; i++) {
            container.appendChild(createPageButton(i, i, i === data.current_page));
        }

        if (endPage < data.pages) {
            if (endPage < data.pages - 1) {
                const span = document.createElement('span');
                span.textContent = '...';
                span.className = 'page-dots';
                container.appendChild(span);
            }
            container.appendChild(createPageButton(data.pages));
        }

        // Next button
        if (data.current_page < data.pages) {
            container.appendChild(createPageButton(data.current_page + 1, '›'));
        }

        // Page info
        const info = document.createElement('div');
        info.className = 'page-info';
        info.textContent = `Page ${data.current_page} of ${data.pages} (${data.total} total)`;
        container.appendChild(info);
    }

    searchUsers() {
        const search = document.getElementById('users-search').value;
        this.loadUsers(1, search);
    }

    searchCollections() {
        const search = document.getElementById('collections-search').value;
        this.loadCollections(1, search);
    }

    confirmAction(action, id, name) {
        this.pendingAction = { action, id, name };
        
        const actionText = {
            'block-user': `block user "${name}"`,
            'unblock-user': `unblock user "${name}"`,
            'block-collection': `block collection "${name}"`,
            'unblock-collection': `unblock collection "${name}"`
        };

        document.getElementById('confirm-title').textContent = 'Confirm Action';
        document.getElementById('confirm-message').textContent = 
            `Are you sure you want to ${actionText[action]}?`;
        
        this.showModal();
    }

    async executeConfirmedAction() {
        if (!this.pendingAction) return;

        const { action, id } = this.pendingAction;
        
        try {
            this.hideModal();
            this.showLoading();

            let endpoint;
            switch (action) {
                case 'block-user':
                    endpoint = `/api/admin/users/${id}/block`;
                    break;
                case 'unblock-user':
                    endpoint = `/api/admin/users/${id}/unblock`;
                    break;
                case 'block-collection':
                    endpoint = `/api/admin/collections/${id}/block`;
                    break;
                case 'unblock-collection':
                    endpoint = `/api/admin/collections/${id}/unblock`;
                    break;
            }

            await api.post(endpoint);
            
            // Refresh current tab
            if (this.currentTab === 'users') {
                this.loadUsers(this.currentUsersPage);
            } else if (this.currentTab === 'collections') {
                this.loadCollections(this.currentCollectionsPage);
            }
            
            // Refresh stats
            this.loadStats();
            
            this.showSuccess('Action completed successfully');
        } catch (error) {
            console.error('Error executing action:', error);
            this.showError('Failed to execute action');
        } finally {
            this.hideLoading();
            this.pendingAction = null;
        }
    }

    formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    }

    showLoading() {
        document.getElementById('loading').classList.remove('hidden');
    }

    hideLoading() {
        document.getElementById('loading').classList.add('hidden');
    }

    showModal() {
        document.getElementById('confirm-modal').classList.remove('hidden');
    }

    hideModal() {
        document.getElementById('confirm-modal').classList.add('hidden');
    }

    showError(message) {
        // You can implement a toast notification system here
        alert('Error: ' + message);
    }

    showSuccess(message) {
        // You can implement a toast notification system here
        alert('Success: ' + message);
    }
}

// Initialize admin panel when page loads
let adminPanel;
document.addEventListener('DOMContentLoaded', () => {
    adminPanel = new AdminPanel();
});