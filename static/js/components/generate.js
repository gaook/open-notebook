/**
 * 内容生成面板
 */

import { generateContent, listGenerated, getGenerated, deleteGenerated, getDocumentImages } from '../api.js';
import { el, showToast, renderMarkdown } from '../utils.js';

const GENERATE_TYPES = [
    { type: 'summary', icon: '📝', title: '文档摘要', desc: '生成结构化的内容摘要' },
    { type: 'faq', icon: '❓', title: '常见问题', desc: '提取 FAQ 问答列表' },
    { type: 'study_guide', icon: '📚', title: '学习指南', desc: '创建学习要点和指南' },
    { type: 'timeline', icon: '📅', title: '时间线', desc: '按时间顺序整理事件' },
    { type: 'translate', icon: '🌐', title: '文档翻译', desc: '将文档翻译为中文' },
];

const TYPE_ICONS = { summary: '📝', faq: '❓', study_guide: '📚', timeline: '📅', note: '💬', translate: '🌐' };

let _refreshFn = null;

export function refreshGenerated(notebookId) {
    if (_refreshFn) _refreshFn();
}

export function renderGenerate(panel, notebookId) {
    panel.innerHTML = '';

    const header = el('div', { className: 'panel-header' },
        el('h3', {}, '内容生成'),
    );
    panel.appendChild(header);

    const body = el('div', { className: 'panel-body' });

    // 生成按钮
    const buttons = el('div', { className: 'generate-buttons' });
    let isGenerating = false;

    for (const gt of GENERATE_TYPES) {
        const btn = el('button', {
            className: 'generate-btn',
            onclick: () => startGenerate(gt.type, btn),
        },
            el('div', { className: 'generate-btn-icon' }, gt.icon),
            el('div', { className: 'generate-btn-text' },
                el('div', { className: 'generate-btn-title' }, gt.title),
                el('div', { className: 'generate-btn-desc' }, gt.desc)
            )
        );
        buttons.appendChild(btn);
    }
    body.appendChild(buttons);

    // 流式预览区
    const preview = el('div', {
        className: 'stream-preview',
        style: { display: 'none' },
    });
    body.appendChild(preview);

    // 已生成内容列表标题
    const listHeader = el('div', {
        style: { fontSize: '13px', fontWeight: '600', marginBottom: '8px', color: 'var(--text-secondary)' },
    }, '已生成内容');
    body.appendChild(listHeader);

    const generatedList = el('div', { className: 'generated-list' });
    body.appendChild(generatedList);

    panel.appendChild(body);

    function startGenerate(type, btn) {
        if (isGenerating) return;
        isGenerating = true;

        // 禁用所有按钮
        buttons.querySelectorAll('.generate-btn').forEach(b => b.disabled = true);

        preview.style.display = 'block';
        preview.innerHTML = '<span class="loading-dots">生成中</span>';
        let fullText = '';

        generateContent(notebookId, type, {
            onChunk(chunk) {
                fullText += chunk;
                preview.innerHTML = renderMarkdown(fullText);
                preview.scrollTop = preview.scrollHeight;
            },
            onDone(data) {
                isGenerating = false;
                buttons.querySelectorAll('.generate-btn').forEach(b => b.disabled = false);
                setTimeout(() => {
                    preview.style.display = 'none';
                    preview.innerHTML = '';
                    loadGenerated();
                }, 1000);
            },
            onError(msg) {
                isGenerating = false;
                buttons.querySelectorAll('.generate-btn').forEach(b => b.disabled = false);
                preview.innerHTML = `<span style="color: var(--danger)">生成失败: ${msg}</span>`;
                showToast(msg, 'error');
            },
        });
    }

    function _buildImagesForPage(images, pageNum) {
        /** 构建某一页的所有图片 HTML */
        let html = '';
        for (const img of images) {
            if (img.page === pageNum) {
                html += `<figure style="margin:16px 0;text-align:center"><img src="${img.data_uri}" style="max-width:100%;height:auto;border:1px solid #eee;border-radius:4px"><figcaption style="color:#999;font-size:12px;margin-top:4px">${img.filename} — 第 ${img.page} 页</figcaption></figure>\n`;
            }
        }
        return html;
    }

    async function downloadHtml(nbId, itemId, title) {
        try {
            showToast('正在准备下载...', 'info');
            // 并行获取翻译内容和文档图片
            const [item, imgData] = await Promise.all([
                getGenerated(nbId, itemId),
                getDocumentImages(nbId),
            ]);

            const images = imgData.images || [];
            let content = item.content || '';

            // 收集所有出现过的页码
            const pageMarkerRe = /<!-- PAGE:(\d+) -->/g;
            const hasPageMarkers = pageMarkerRe.test(content);
            pageMarkerRe.lastIndex = 0; // 重置

            let bodyHtml;
            if (hasPageMarkers && images.length > 0) {
                // 按 <!-- PAGE:N --> 标记拆分，在每个标记位置插入该页图片
                // 先用 HTML comment 兼容占位符替换，marked 会保留 HTML comment
                let idx = 0;
                const placeholders = [];
                content = content.replace(pageMarkerRe, (match, pageStr) => {
                    const pageNum = parseInt(pageStr);
                    const ph = `XPAGEIMG_${idx}_XPAGEIMG`;
                    placeholders.push({ pageNum, ph });
                    idx++;
                    return ph;
                });

                // 渲染 Markdown + KaTeX
                bodyHtml = renderMarkdown(content);

                // 替换占位符为实际图片 HTML
                for (const { pageNum, ph } of placeholders) {
                    const imgHtml = _buildImagesForPage(images, pageNum);
                    bodyHtml = bodyHtml.replace(ph, imgHtml);
                }
            } else {
                // 没有页码标记，清理标记后渲染，图片放末尾
                content = content.replace(/<!-- PAGE:\d+ -->/g, '');
                bodyHtml = renderMarkdown(content);
                if (images.length > 0) {
                    bodyHtml += '<hr><h2>原文图片</h2>\n';
                    let curPage = -1;
                    for (const img of images) {
                        if (img.page !== curPage) {
                            curPage = img.page;
                            bodyHtml += `<h3>${img.filename} — 第 ${img.page} 页</h3>\n`;
                        }
                        bodyHtml += `<figure style="margin:16px 0;text-align:center"><img src="${img.data_uri}" style="max-width:100%;height:auto;border:1px solid #eee;border-radius:4px"></figure>\n`;
                    }
                }
            }

            const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>${title}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<style>
body{max-width:800px;margin:40px auto;padding:0 20px;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;line-height:1.8;color:#1a1a1a}
h1,h2,h3{margin-top:1.5em;color:#111}
code{background:#f4f4f4;padding:2px 6px;border-radius:3px;font-size:0.9em}
pre{background:#f4f4f4;padding:16px;border-radius:6px;overflow-x:auto}
pre code{background:none;padding:0}
blockquote{border-left:4px solid #ddd;margin:1em 0;padding:0.5em 1em;color:#555}
table{border-collapse:collapse;width:100%}
th,td{border:1px solid #ddd;padding:8px 12px;text-align:left}
th{background:#f8f8f8}
figure{text-align:center}
</style>
</head>
<body>
<h1>${title}</h1>
${bodyHtml}
<hr><p style="color:#999;font-size:12px">由 Open Notebook 生成</p>
</body>
</html>`;
            const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${title}.html`;
            a.click();
            URL.revokeObjectURL(url);
            showToast('已下载 HTML 文件', 'info');
        } catch (e) {
            showToast(e.message, 'error');
        }
    }

    async function loadGenerated() {
        try {
            const { items } = await listGenerated(notebookId);
            generatedList.innerHTML = '';

            if (items.length === 0) {
                generatedList.appendChild(el('div', {
                    style: { textAlign: 'center', padding: '16px', color: 'var(--text-muted)', fontSize: '12px' },
                }, '暂无生成内容'));
                listHeader.style.display = 'none';
                return;
            }

            listHeader.style.display = 'block';

            for (const item of items) {
                const icon = TYPE_ICONS[item.content_type] || '📄';
                const itemEl = el('div', { className: 'generated-item' },
                    el('div', { className: 'generated-item-title' },
                        `${icon} ${item.title}`
                    ),
                    el('div', {
                        className: 'generated-item-meta',
                        style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
                    },
                        el('span', {}, item.created_at?.slice(0, 16).replace('T', ' ') || ''),
                        ...(item.content_type === 'translate' ? [el('button', {
                            className: 'btn btn-sm btn-ghost',
                            onclick: (e) => { e.stopPropagation(); downloadHtml(notebookId, item.id, item.title); },
                            style: { fontSize: '11px', color: 'var(--primary)' },
                        }, '下载')] : []),
                        el('button', {
                            className: 'btn btn-sm btn-ghost',
                            onclick: async (e) => {
                                e.stopPropagation();
                                if (!confirm('确定删除？')) return;
                                await deleteGenerated(notebookId, item.id);
                                loadGenerated();
                            },
                            style: { fontSize: '11px', color: 'var(--danger)' },
                        }, '删除')
                    )
                );
                itemEl.addEventListener('click', () => showGeneratedContent(notebookId, item.id, item.title));
                generatedList.appendChild(itemEl);
            }
        } catch (e) {
            /* 静默 */
        }
    }

    async function showGeneratedContent(notebookId, itemId, title) {
        try {
            const item = await getGenerated(notebookId, itemId);
            // 清除页码标记，在弹窗中不显示
            const cleanContent = (item.content || '').replace(/<!-- PAGE:\d+ -->/g, '');

            const overlay = el('div', { className: 'modal-overlay' });
            const modal = el('div', { className: 'modal' },
                el('div', { className: 'modal-header' },
                    el('h3', {}, title),
                    el('button', {
                        className: 'btn-icon',
                        onclick: () => overlay.remove(),
                        innerHTML: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
                    })
                ),
                el('div', {
                    className: 'modal-body',
                    innerHTML: renderMarkdown(cleanContent),
                })
            );
            overlay.appendChild(modal);
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) overlay.remove();
            });
            document.body.appendChild(overlay);
        } catch (e) {
            showToast(e.message, 'error');
        }
    }

    _refreshFn = loadGenerated;
    loadGenerated();
}
