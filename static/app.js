// DOM Elements
const elements = {
    chatMessagesContainer: document.getElementById('chat-messages-container'),
    welcomeScreen: document.getElementById('welcome-screen'),
    chatForm: document.getElementById('chat-form'),
    chatInput: document.getElementById('chat-input'),
    sendBtn: document.getElementById('send-btn'),
    newChatBtn: document.getElementById('new-chat-btn'),
    toast: document.getElementById('toast-notification'),
    toastMessage: document.getElementById('toast-message'),
    suggestionsBox: document.getElementById('suggestions-box')
};

// Initialize application
document.addEventListener('DOMContentLoaded', () => {
    bindEvents();
    updateSendButtonState();
});

// Event Binding
function bindEvents() {
    // Chat Actions
    elements.chatForm.addEventListener('submit', handleChatSubmit);
    elements.chatInput.addEventListener('input', updateSendButtonState);
    elements.newChatBtn.addEventListener('click', clearChatHistory);

    // Suggestion chips
    document.querySelectorAll('.suggestion-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const question = chip.getAttribute('data-question');
            elements.chatInput.value = question;
            updateSendButtonState();
            elements.chatInput.focus();
        });
    });
}

function updateSendButtonState() {
    const hasText = !!elements.chatInput.value.trim();
    elements.sendBtn.disabled = !hasText;
}

// Conversational Interface Logic
async function handleChatSubmit(e) {
    e.preventDefault();
    const query = elements.chatInput.value.trim();
    if (!query) return;

    // 1. Add User Message
    addMessage(query, 'user');
    elements.chatInput.value = '';
    updateSendButtonState();

    // 2. Hide welcome screen if first message
    if (elements.welcomeScreen) {
        elements.welcomeScreen.style.display = 'none';
    }

    // 3. Add bot message loading indicator
    const botMsgId = 'bot-response-' + Date.now();
    addMessage('', 'bot', botMsgId, true);
    scrollToBottom();

    // 4. Send API query
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: query
            })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Fallo al procesar tu consulta.');
        }

        const data = await response.json();
        
        // Remove typing indicator and populate answer with sources
        updateBotMessage(botMsgId, data.answer, data.sources);
    } catch (e) {
        console.error(e);
        updateBotMessage(botMsgId, `⚠️ **Error en consulta:** ${e.message || 'No se pudo obtener una respuesta del servidor.'}`, []);
    } finally {
        scrollToBottom();
    }
}

function addMessage(text, sender, id = null, isLoading = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message message-${sender}`;
    if (id) msgDiv.id = id;

    const avatarHtml = sender === 'user' 
        ? '<i class="fa-solid fa-user"></i>' 
        : '<i class="fa-solid fa-robot"></i>';

    const bubbleContent = isLoading 
        ? `<div class="typing-indicator"><span></span><span></span><span></span></div>`
        : formatMarkdown(text);

    msgDiv.innerHTML = `
        <div class="message-avatar">${avatarHtml}</div>
        <div class="message-bubble-wrapper">
            <div class="message-bubble">${bubbleContent}</div>
            <div class="message-meta">${sender === 'user' ? 'Tú' : 'Asistente DocuMind'} • ${getCurrentTime()}</div>
        </div>
    `;

    elements.chatMessagesContainer.appendChild(msgDiv);
    scrollToBottom();
}

function updateBotMessage(id, answer, sources) {
    const msgDiv = document.getElementById(id);
    if (!msgDiv) return;

    const bubble = msgDiv.querySelector('.message-bubble');
    bubble.innerHTML = formatMarkdown(answer);

    // Add sources if available
    if (sources && sources.length > 0) {
        const sourcesId = 'sources-' + id;
        const sourcesCard = document.createElement('div');
        sourcesCard.className = 'sources-card';
        
        let sourcesItemsHtml = '';
        sources.forEach((src, idx) => {
            const textSnippet = src.snippet.length > 100 ? src.snippet.slice(0, 100) + '...' : src.snippet;
            sourcesItemsHtml += `
                <li class="source-item">
                    <div class="source-item-header">
                        <span><i class="fa-solid fa-file"></i> ${src.file}</span>
                        <span>Fragmento #${idx + 1} (Pág. ${src.page})</span>
                    </div>
                    <div class="source-snippet" title="${src.snippet.replace(/"/g, '&quot;')}">
                        "${textSnippet}"
                    </div>
                </li>
            `;
        });

        sourcesCard.innerHTML = `
            <button class="sources-toggle" onclick="toggleSourcesDrawer('${sourcesId}')">
                <i class="fa-solid fa-chevron-down" id="arrow-${sourcesId}"></i> Ver fuentes y referencias (${sources.length})
            </button>
            <ul class="sources-list" id="${sourcesId}" style="display: none;">
                ${sourcesItemsHtml}
            </ul>
        `;
        
        msgDiv.querySelector('.message-bubble-wrapper').appendChild(sourcesCard);
    }
}

function toggleSourcesDrawer(id) {
    const list = document.getElementById(id);
    const arrow = document.getElementById('arrow-' + id);
    if (list.style.display === 'none') {
        list.style.display = 'flex';
        arrow.className = 'fa-solid fa-chevron-up';
    } else {
        list.style.display = 'none';
        arrow.className = 'fa-solid fa-chevron-down';
    }
    scrollToBottom();
}

function clearChatHistory() {
    // Retain only welcome screen
    elements.chatMessagesContainer.innerHTML = '';
    if (elements.welcomeScreen) {
        elements.welcomeScreen.style.display = 'flex';
        elements.chatMessagesContainer.appendChild(elements.welcomeScreen);
    }
    updateSendButtonState();
}

// Utilities
function scrollToBottom() {
    elements.chatMessagesContainer.scrollTop = elements.chatMessagesContainer.scrollHeight;
}

function getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function showToast(message, isError = false) {
    elements.toastMessage.textContent = message;
    
    if (isError) {
        elements.toast.style.borderLeft = '4px solid #f43f5e';
        elements.toast.querySelector('.toast-icon').className = 'fa-solid fa-circle-exclamation toast-icon';
        elements.toast.querySelector('.toast-icon').style.color = '#f43f5e';
    } else {
        elements.toast.style.borderLeft = '4px solid #6366f1';
        elements.toast.querySelector('.toast-icon').className = 'fa-solid fa-circle-info toast-icon';
        elements.toast.querySelector('.toast-icon').style.color = '#6366f1';
    }

    elements.toast.classList.add('show');
    
    // Auto-hide toast after 4.5 seconds
    setTimeout(() => {
        elements.toast.classList.remove('show');
    }, 4500);
}

// A simple client-side markdown formatter for bullet points, bolding and paragraphs
function formatMarkdown(text) {
    if (!text) return '';
    let formatted = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Code blocks `code`
    formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // Bold text **bold**
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    
    // Bullets (starting with "- " or "* " or "• ")
    const lines = formatted.split('\n');
    let inList = false;
    let listType = ''; // 'ul' or 'ol'
    
    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        
        // List element checks
        if (line.startsWith('- ') || line.startsWith('* ') || line.startsWith('• ')) {
            let content = line.substring(2);
            if (!inList) {
                lines[i] = '<ul><li>' + content + '</li>';
                inList = true;
                listType = 'ul';
            } else {
                lines[i] = '<li>' + content + '</li>';
            }
        } else if (/^\d+\.\s/.test(line)) { // numbered list
            let content = line.substring(line.indexOf('.') + 1).trim();
            if (!inList) {
                lines[i] = '<ol><li>' + content + '</li>';
                inList = true;
                listType = 'ol';
            } else {
                lines[i] = '<li>' + content + '</li>';
            }
        } else {
            if (inList) {
                lines[i - 1] = lines[i - 1] + `</${listType}>`;
                inList = false;
            }
            if (line.length > 0) {
                lines[i] = `<p>${line}</p>`;
            }
        }
    }
    
    if (inList) {
        lines[lines.length - 1] = lines[lines.length - 1] + `</${listType}>`;
    }

    return lines.join('\n');
}
