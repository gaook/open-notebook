/**
 * API 调用封装
 */

const API_BASE = '/api';

async function request(path, options = {}) {
    const resp = await fetch(`${API_BASE}${path}`, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
    });
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail || '请求失败');
    }
    return resp.json();
}

// ---- 笔记本 ----
export async function listNotebooks() {
    return request('/notebooks');
}

export async function createNotebook(title = '未命名笔记本') {
    return request('/notebooks', {
        method: 'POST',
        body: JSON.stringify({ title }),
    });
}

export async function getNotebook(id) {
    return request(`/notebooks/${id}`);
}

export async function updateNotebook(id, data) {
    return request(`/notebooks/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
    });
}

export async function deleteNotebook(id) {
    return request(`/notebooks/${id}`, { method: 'DELETE' });
}

// ---- 文档 ----
export async function listDocuments(notebookId) {
    return request(`/notebooks/${notebookId}/documents`);
}

export async function uploadDocument(notebookId, file) {
    const formData = new FormData();
    formData.append('file', file);
    const resp = await fetch(`${API_BASE}/notebooks/${notebookId}/documents`, {
        method: 'POST',
        body: formData,
    });
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail || '上传失败');
    }
    return resp.json();
}

export async function deleteDocument(notebookId, docId) {
    return request(`/notebooks/${notebookId}/documents/${docId}`, { method: 'DELETE' });
}

// ---- 对话 ----
export async function getChatHistory(notebookId) {
    return request(`/notebooks/${notebookId}/chat/history`);
}

export function chatStream(notebookId, message, callbacks) {
    const controller = new AbortController();

    fetch(`${API_BASE}/notebooks/${notebookId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
        signal: controller.signal,
    }).then(async (resp) => {
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                try {
                    const data = JSON.parse(line.slice(6));
                    if (data.type === 'chunk' && callbacks.onChunk) {
                        callbacks.onChunk(data.content);
                    } else if (data.type === 'sources' && callbacks.onSources) {
                        callbacks.onSources(data.sources);
                    } else if (data.type === 'done' && callbacks.onDone) {
                        callbacks.onDone(data);
                    } else if (data.type === 'error' && callbacks.onError) {
                        callbacks.onError(data.message);
                    }
                } catch (e) { /* ignore parse errors */ }
            }
        }
        if (callbacks.onDone && !buffer) callbacks.onDone({});
    }).catch((err) => {
        if (err.name !== 'AbortError' && callbacks.onError) {
            callbacks.onError(err.message);
        }
    });

    return controller;
}

export async function clearChatHistory(notebookId) {
    return request(`/notebooks/${notebookId}/chat/history`, { method: 'DELETE' });
}

// ---- 内容生成 ----
export function generateContent(notebookId, type, callbacks) {
    const controller = new AbortController();

    fetch(`${API_BASE}/notebooks/${notebookId}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type }),
        signal: controller.signal,
    }).then(async (resp) => {
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: resp.statusText }));
            if (callbacks.onError) callbacks.onError(err.detail || '生成失败');
            return;
        }

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                try {
                    const data = JSON.parse(line.slice(6));
                    if (data.type === 'chunk' && callbacks.onChunk) {
                        callbacks.onChunk(data.content);
                    } else if (data.type === 'done' && callbacks.onDone) {
                        callbacks.onDone(data);
                    } else if (data.type === 'error' && callbacks.onError) {
                        callbacks.onError(data.message);
                    }
                } catch (e) { /* ignore */ }
            }
        }
    }).catch((err) => {
        if (err.name !== 'AbortError' && callbacks.onError) {
            callbacks.onError(err.message);
        }
    });

    return controller;
}

export async function listGenerated(notebookId) {
    return request(`/notebooks/${notebookId}/generated`);
}

export async function getGenerated(notebookId, itemId) {
    return request(`/notebooks/${notebookId}/generated/${itemId}`);
}

export async function deleteGenerated(notebookId, itemId) {
    return request(`/notebooks/${notebookId}/generated/${itemId}`, { method: 'DELETE' });
}

export async function saveNote(notebookId, title, content) {
    return request(`/notebooks/${notebookId}/generated/note`, {
        method: 'POST',
        body: JSON.stringify({ title, content }),
    });
}

// ---- 设置 ----
export async function getSettings() {
    return request('/settings');
}

export async function updateSettings(data) {
    return request('/settings', {
        method: 'PUT',
        body: JSON.stringify(data),
    });
}

export async function testConnection() {
    return request('/settings/test', { method: 'POST' });
}
