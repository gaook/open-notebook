/**
 * 对话面板
 */

import { getChatHistory, chatStream, clearChatHistory } from '../api.js';
import { el, showToast, renderMarkdown } from '../utils.js';

export function renderChat(panel, notebookId) {
    panel.innerHTML = '';

    const header = el('div', { className: 'panel-header' },
        el('h3', {}, '对话'),
        el('button', {
            className: 'btn btn-sm btn-ghost',
            title: '清除对话',
            onclick: async () => {
                if (!confirm('确定清除所有对话历史？')) return;
                try {
                    await clearChatHistory(notebookId);
                    messagesContainer.innerHTML = '';
                    showToast('对话已清除', 'info');
                } catch (e) {
                    showToast(e.message, 'error');
                }
            },
        }, '清除')
    );
    panel.appendChild(header);

    // 消息列表
    const messagesContainer = el('div', { className: 'chat-messages' });
    panel.appendChild(messagesContainer);

    // 输入区域
    const inputArea = el('div', { className: 'chat-input-area' });
    const textarea = el('textarea', {
        className: 'chat-input',
        placeholder: '输入你的问题...',
    });
    textarea.rows = 1;

    const sendBtn = el('button', {
        className: 'chat-send-btn',
        innerHTML: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>',
    });

    const inputWrapper = el('div', { className: 'chat-input-wrapper' });
    inputWrapper.appendChild(textarea);
    inputWrapper.appendChild(sendBtn);
    inputArea.appendChild(inputWrapper);
    panel.appendChild(inputArea);

    let isStreaming = false;

    // 自动调整高度
    textarea.addEventListener('input', () => {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    });

    // Enter 发送，Shift+Enter 换行
    textarea.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    sendBtn.addEventListener('click', sendMessage);

    function sendMessage() {
        const message = textarea.value.trim();
        if (!message || isStreaming) return;

        textarea.value = '';
        textarea.style.height = 'auto';

        // 添加用户消息气泡
        addMessage('user', message);

        // 创建助手消息气泡（流式填充）
        const assistantBubble = addMessage('assistant', '');
        const bubbleContent = assistantBubble.querySelector('.message-bubble');
        let fullText = '';

        isStreaming = true;
        sendBtn.disabled = true;

        chatStream(notebookId, message, {
            onChunk(chunk) {
                fullText += chunk;
                bubbleContent.innerHTML = renderMarkdown(fullText);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            },
            onSources(sources) {
                if (sources && sources.length > 0) {
                    const sourcesDiv = el('div', { className: 'message-sources' });
                    for (const src of sources) {
                        sourcesDiv.appendChild(
                            el('span', { className: 'source-chip', title: src.snippet },
                                `📄 ${src.filename}`)
                        );
                    }
                    assistantBubble.appendChild(sourcesDiv);
                }
            },
            onDone() {
                isStreaming = false;
                sendBtn.disabled = false;
                textarea.focus();
            },
            onError(msg) {
                isStreaming = false;
                sendBtn.disabled = false;
                if (!fullText) {
                    bubbleContent.innerHTML = `<span style="color: var(--danger)">错误: ${msg}</span>`;
                }
                showToast(msg, 'error');
            },
        });
    }

    function addMessage(role, content) {
        const avatar = role === 'user' ? '我' : 'AI';
        const msg = el('div', { className: `message ${role}` },
            el('div', { className: 'message-avatar' }, avatar),
            el('div', {
                className: 'message-bubble',
                innerHTML: content ? renderMarkdown(content) : '<span class="loading-dots">思考中</span>',
            })
        );
        messagesContainer.appendChild(msg);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        return msg;
    }

    // 加载历史消息
    async function loadHistory() {
        try {
            const { messages } = await getChatHistory(notebookId);
            for (const msg of messages) {
                const bubble = addMessage(msg.role, msg.content);
                // 添加来源标记
                if (msg.role === 'assistant' && msg.sources) {
                    try {
                        const sources = JSON.parse(msg.sources);
                        if (sources && sources.length > 0) {
                            const sourcesDiv = el('div', { className: 'message-sources' });
                            for (const src of sources) {
                                sourcesDiv.appendChild(
                                    el('span', { className: 'source-chip', title: src.snippet || '' },
                                        `📄 ${src.filename}`)
                                );
                            }
                            bubble.appendChild(sourcesDiv);
                        }
                    } catch (e) { /* ignore */ }
                }
            }
        } catch (e) {
            // 静默处理
        }
    }

    loadHistory();
}
