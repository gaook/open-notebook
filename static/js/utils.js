/**
 * 工具函数
 */

/**
 * 渲染 Markdown 为 HTML
 */
export function renderMarkdown(text) {
    if (typeof marked !== 'undefined') {
        return marked.parse(text || '');
    }
    // 简单回退：只处理基本格式
    return (text || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\n/g, '<br>');
}

/**
 * 创建 DOM 元素
 */
export function el(tag, attrs = {}, ...children) {
    const elem = document.createElement(tag);
    for (const [key, val] of Object.entries(attrs)) {
        if (key === 'className') elem.className = val;
        else if (key === 'onclick') elem.onclick = val;
        else if (key === 'innerHTML') elem.innerHTML = val;
        else if (key === 'style' && typeof val === 'object') {
            Object.assign(elem.style, val);
        } else {
            elem.setAttribute(key, val);
        }
    }
    for (const child of children) {
        if (typeof child === 'string') {
            elem.appendChild(document.createTextNode(child));
        } else if (child) {
            elem.appendChild(child);
        }
    }
    return elem;
}

/**
 * 显示通知
 */
export function showToast(message, type = 'info') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = el('div', { className: 'toast-container' });
        document.body.appendChild(container);
    }

    const toast = el('div', { className: `toast toast-${type}` }, message);
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(40px)';
        toast.style.transition = '0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * 格式化文件大小
 */
export function formatSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * 格式化时间
 */
export function formatTime(isoString) {
    if (!isoString) return '';
    const d = new Date(isoString + 'Z');
    const now = new Date();
    const diff = now - d;
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`;
    return d.toLocaleDateString('zh-CN');
}
