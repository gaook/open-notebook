/**
 * 工具函数
 */

/**
 * 渲染 Markdown + LaTeX 数学公式为 HTML
 * 流程：提取数学公式 → marked 渲染 Markdown → 还原 KaTeX 渲染结果
 */
export function renderMarkdown(text) {
    if (!text) return '';

    const mathBlocks = [];
    let processed = text;

    if (typeof katex !== 'undefined') {
        // 1) 显示公式 $$...$$ (含换行)
        processed = processed.replace(/\$\$([\s\S]+?)\$\$/g, (_, expr) => {
            const placeholder = `\x00MATH${mathBlocks.length}\x00`;
            try {
                mathBlocks.push(katex.renderToString(expr.trim(), { displayMode: true, throwOnError: false }));
            } catch { mathBlocks.push(`<code>${expr}</code>`); }
            return placeholder;
        });
        // 2) 行内公式 $...$ (不跨行，避免匹配货币符号)
        processed = processed.replace(/\$([^\n$]+?)\$/g, (_, expr) => {
            const placeholder = `\x00MATH${mathBlocks.length}\x00`;
            try {
                mathBlocks.push(katex.renderToString(expr.trim(), { displayMode: false, throwOnError: false }));
            } catch { mathBlocks.push(`<code>${expr}</code>`); }
            return placeholder;
        });
    }

    // Markdown 渲染
    let html;
    if (typeof marked !== 'undefined') {
        html = marked.parse(processed);
    } else {
        html = processed
            .replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/\n/g, '<br>');
    }

    // 还原数学公式
    for (let i = 0; i < mathBlocks.length; i++) {
        html = html.replace(`\x00MATH${i}\x00`, mathBlocks[i]);
    }
    return html;
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
