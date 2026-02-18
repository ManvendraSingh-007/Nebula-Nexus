(function () {
    const chatContainer = document.getElementById('messagesFeed');
    const sendBtn = document.getElementById('sendButton');
    const input = document.getElementById('chatInput');

    const pendingMessages = new Map();
    // stores temporary message id's

    const init = () => {
        if (!chatContainer) return;
        // returns back if message container not found

        loadHistory();
        // load the history of chat

        sendBtn?.addEventListener('click', sendMessage);
        input?.addEventListener('keypress', (e) => {
            if (e.key == 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        })
    }

    // Setup WebSocket listeners for chat
    if (window.socketService) {
        // Listen for chat messages
        window.socketService.addEventListener('chat', handleIncomingMessage);

        // Listen for message sent confirmation
        window.socketService.addEventListener('message_sent', handleMessageSent);

        // Listen for user status updates (online/offline)
        window.socketService.addEventListener('user_status', handleUserStatus);
    }

    function handleIncomingMessage(event) {
        const data = event.detail

        if (data.sender_id == receiverId) {
            appendMessageToUI({
                content: data.content,
                timestamp: data.timestamp,
                isMe: data.sender_id == userId
            });

            updateSidebarBadge(data.sender_id, 0);
        }
    }

    function handleMessageSent(event) {
        const data = event.detail;

        // Update the temporary message with DB timestamp
        const messageElement = document.querySelector(`[data-temp-id="${data.temp_id}"]`);
        if (messageElement) {
            const timeElement = messageElement.querySelector('.message-time');
            if (timeElement && data.timestamp) {
                timeElement.textContent = formatTime(data.timestamp);
            }
            messageElement.dataset.messageId = data.message_id;
            messageElement.removeAttribute('data-temp-id');
        }
    }

    function handleUserStatus(event) {
        const data = event.detail;

        // Update sidebar status for this user
        const userElement = document.querySelector(`[data-user-id="${data.user_id}"]`);
        if (userElement) {
            const statusDot = userElement.querySelector('.status-dot');
            if (statusDot) {
                statusDot.className = `status-dot ${data.is_online ? 'online' : 'offline'}`;

            }
        }

        const currentReceiverId = receiverId; // This should be available in chat.js
        if (data.user_id == currentReceiverId) {
            console.log("sjdhfisfhiusfhiushfei")
            // Find header specifically
            const headerStatusDot = document.querySelector('.chat-header .status-dot');
            if (headerStatusDot) {
                headerStatusDot.className = `status-dot ${data.is_online ? 'online' : 'offline'}`;
            }
        }
    }

    function formatTime(timestamp) {
        if (!timestamp) return;
        return new Date(timestamp).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
        })
        // returns time in a local timezone
    }

    function appendMessageToUI(data) {
        if (!chatContainer) return;

        const messageType = data.isMe ? 'sent' : 'received';
        const avatarName = data.isMe ? userName : receiverName;
        const initial = avatarName[0].toUpperCase();

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${messageType}`;

        if (data.tempId) {
            messageDiv.setAttribute('data-temp-id', data.tempId);
        }

        // Add permanent ID if provided
        if (data.id) {
            messageDiv.setAttribute('data-message-id', data.id);
        }

        const avatarHTML = messageType === 'received' ? `<div class="user-avatar">${initial}</div>` : '';
        messageDiv.innerHTML = `
                ${avatarHTML}
                <div class="message-content">
                    <div class="message-bubble"></div>
                    <div class="message-time">${formatTime(data.timestamp) || 'Just now'}</div>
                </div>
            `;

        messageDiv.querySelector('.message-bubble').textContent = data.content;
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function updateSidebarBadge(userId, count) {
        const userElement = document.querySelector(`[data-user-id="${userId}"]`);
        if (userElement) {
            const badge = userElement.querySelector('.badge');
            if (badge) {
                badge.style.display = count > 0 ? 'flex' : 'none';
                badge.textContent = count > 4 ? '4+' : count;
            }
        }
    }

    async function sendMessage() {
        const text = input.value.trim();
        if (!text || !window.socketService) return;

        const tempId = `temp_${Date.now()}`;
        const clientTimestamp = new Date().toISOString();

        const messageData = {
            content: text,
            timestamp: new Date().toISOString(),
            isMe: true,
            tempId: tempId
        };

        appendMessageToUI(messageData);

        window.socketService.send({
            receiver_id: receiverId,
            content: text,
            tempId: tempId
        });

        input.value = '';
        input.focus();
    }

    async function loadHistory() {
        chatContainer.innerHTML = '<div class="message-history-loading"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-loader-icon lucide-loader"><path d="M12 2v4"/><path d="m16.2 7.8 2.9-2.9"/><path d="M18 12h4"/><path d="m16.2 16.2 2.9 2.9"/><path d="M12 18v4"/><path d="m4.9 19.1 2.9-2.9"/><path d="M2 12h4"/><path d="m4.9 4.9 2.9 2.9"/></svg></div>';

        try {
            const response = await fetch(`/api/messages/${receiverId}`);
            if (!response.ok) throw new Error('Network error');

            const data = await response.json();
            chatContainer.innerHTML = '';

            data.forEach(item => {
                item.isMe = (item.sender_id != receiverId);
                appendMessageToUI(item);
            });

            updateSidebarBadge(receiverId, 0);
        } catch (error) {
            console.error('Failed to load messages:', error);
            chatContainer.innerHTML = '<div class="message-history-error"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-refresh-cw-off-icon lucide-refresh-cw-off"><path d="M21 8L18.74 5.74A9.75 9.75 0 0 0 12 3C11 3 10.03 3.16 9.13 3.47"/><path d="M8 16H3v5"/><path d="M3 12C3 9.51 4 7.26 5.64 5.64"/><path d="m3 16 2.26 2.26A9.75 9.75 0 0 0 12 21c2.49 0 4.74-1 6.36-2.64"/><path d="M21 12c0 1-.16 1.97-.47 2.87"/><path d="M21 3v5h-5"/><path d="M22 22 2 2"/></svg>Failed to load messages</div>';
        }
    }

    document.addEventListener('DOMContentLoaded', init);
})();