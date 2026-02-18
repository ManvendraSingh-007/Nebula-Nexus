async function loadUsers() {
    const res = await fetch('/api/users');
    const users = await res.json(); // Data is [[id, count, name], ...]

    const container = document.getElementById('userList');

    // We destructure [id, unread, name] directly from each user array
    container.innerHTML = users.map(([id, name, unread, isOnline]) => `
        <a class="user-item" href="/nexus/chat/dm/${id}" data-user-id="${id}">
            <div class="user-avatar">
                ${name[0].toUpperCase()}
                <span class="status-dot ${isOnline ? 'online' : 'offline'}"></span>
            </div>
            <div class="user-info">
                <div class="user-name">${name}</div>
                <div class="last-message">Click to start chat</div>
            </div>
            <div class="user-meta">
                <span class="badge" style="display: ${unread > 0 ? 'flex' : 'none'}">
                    ${unread > 4 ? '4+' : unread}
                </span>
                <span class="timestamp">Now</span>
            </div>
        </a>`).join('');
}


class SocketService extends EventTarget {
    constructor(url, user) {
        super();
        this.url = url;
        this.user = user;
        this.socket = null;
        this.reconnectAttempt = 0;
        this.maxReconnectionDelay = 30000;
        this.messageQueue = [];
        this.messageHandlers = new Map();

        this.connect();
    }

    connect() {
        console.log(`Connecting as ${this.user.userName}...`);
        this.socket = new WebSocket(this.url);

        this.socket.onopen = () => {
            console.log('Connected');
            this.reconnectAttempt = 0;
            while (this.messageQueue.length > 0 && this.socket.readyState === WebSocket.OPEN) {
                this.socket.send(this.messageQueue.shift());
            }
            this.dispatchEvent(new CustomEvent('status', { detail: 'connected' }));
            loadUsers();
        }

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type) {
                    this.dispatchEvent(new CustomEvent(data.type, { detail: data }));
                }
            } catch (e) {
                console.error("Malformed JSON received", e);
            }
        }

        this.socket.onclose = () => {
            this.dispatchEvent(new CustomEvent('status', { detail: 'disconnected' }));
            this.scheduleReconnect();
        }

        this.socket.onerror = (error) => {
            console.error(error);
        }
    }


    scheduleReconnect() {
        const delay = Math.min(Math.pow(2, this.reconnectAttempt), this.maxReconnectionDelay) * 1000 // get delay then multiply by 1000 for seconds equivalent
        console.warn(`Reconnecting in ${delay / 1000}`)

        setTimeout(() => {
            this.reconnectAttempt++;
            this.connect();
        }, delay);
    }

    send(payload) {
        const message = JSON.stringify(payload);
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(message);
        } else {
            console.warn("Socket not open. Queueing message...");
            this.messageQueue.push(message);
        }
    }

};

// Global initialization function
function initDashboard(loggedUser) {
    loadUsers();
    if (window.socketService) return;
    const protocol = (window.location.protocol === "https:") ? "wss:" : "ws:";
    const domain = window.location.host;
    const socketUrl = `${protocol}//${domain}/ws/${encodeURIComponent(loggedUser.userId)}`;

    // Create a global instance so you can call socketService.send() from anywhere
    window.socketService = new SocketService(socketUrl, loggedUser);

    window.socketService.addEventListener('user_status', handleUserStatusUpdate);
    window.socketService.addEventListener('chat', handleChatUpdate);
}

function handleUserStatusUpdate(event) {
    const data = event.detail;

    // Update status dot in sidebar
    const userElement = document.querySelector(`[data-user-id="${data.user_id}"]`);
    if (userElement) {
        const statusDot = userElement.querySelector('.status-dot');
        if (statusDot) {
            statusDot.className = `status-dot ${data.is_online ? 'online' : 'offline'}`;
        }
    }
}

function handleChatUpdate(event) {
    const data = event.detail;

    // If we're not currently in chat with this sender, update their badge
    const currentPath = window.location.pathname;
    const isInChatWithSender = currentPath.includes(`/nexus/chat/dm/${data.sender_id}`);

    if (!isInChatWithSender) {
        const userElement = document.querySelector(`[data-user-id="${data.sender_id}"]`);
        if (userElement) {
            const badge = userElement.querySelector('.badge');
            if (badge) {
                const currentCount = parseInt(badge.textContent) || 0;
                const newCount = currentCount + 1;
                badge.style.display = 'flex';
                badge.textContent = newCount > 4 ? '4+' : newCount;
            }
        }
    }
}