/**
 * 对话面板
 */

import { getChatHistory, chatStream, clearChatHistory, saveNote } from '../api.js';
import { el, showToast, renderMarkdown } from '../utils.js';

export function renderChat(panel, notebookId, callbacks = {}) {
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

    // Shift+Enter 发送，Enter 换行
    textarea.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.shiftKey) {
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
            onSources() {},
            onDone() {
                isStreaming = false;
                sendBtn.disabled = false;
                textarea.focus();
                if (fullText) {
                    const actions = el('div', { className: 'message-actions' });
                    actions.appendChild(createCopyBtn(fullText));
                    actions.appendChild(createSaveBtn(fullText));
                    assistantBubble.appendChild(actions);
                }
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

    function createCopyBtn(msgContent) {
        const btn = el('button', {
            className: 'message-action-btn',
            title: '复制到剪贴板',
            onclick: async () => {
                try {
                    await navigator.clipboard.writeText(msgContent);
                    btn.textContent = '已复制';
                    showToast('已复制到剪贴板', 'info');
                    setTimeout(() => { btn.textContent = '复制'; }, 1500);
                } catch (e) {
                    showToast('复制失败', 'error');
                }
            },
        }, '复制');
        return btn;
    }

    function createSaveBtn(msgContent) {
        const btn = el('button', {
            className: 'message-action-btn',
            title: '保存为笔记',
            onclick: async () => {
                try {
                    btn.disabled = true;
                    btn.textContent = '保存中...';
                    const title = '对话笔记 ' + new Date().toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
                    await saveNote(notebookId, title, msgContent);
                    btn.textContent = '已保存';
                    showToast('已保存为笔记', 'info');
                    if (callbacks.onNoteSaved) callbacks.onNoteSaved();
                } catch (e) {
                    btn.disabled = false;
                    btn.textContent = '保存为笔记';
                    showToast(e.message, 'error');
                }
            },
        }, '保存为笔记');
        return btn;
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
        if (role === 'assistant' && content) {
            const actions = el('div', { className: 'message-actions' });
            actions.appendChild(createCopyBtn(content));
            actions.appendChild(createSaveBtn(content));
            msg.appendChild(actions);
        }
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
            }
        } catch (e) {
            // 静默处理
        }
    }

    loadHistory();
}
