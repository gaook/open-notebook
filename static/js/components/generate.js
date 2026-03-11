/**
 * 内容生成面板
 */

import { generateContent, listGenerated, getGenerated, deleteGenerated } from '../api.js';
import { el, showToast, renderMarkdown } from '../utils.js';

const GENERATE_TYPES = [
    { type: 'summary', icon: '📝', title: '文档摘要', desc: '生成结构化的内容摘要' },
    { type: 'faq', icon: '❓', title: '常见问题', desc: '提取 FAQ 问答列表' },
    { type: 'study_guide', icon: '📚', title: '学习指南', desc: '创建学习要点和指南' },
    { type: 'timeline', icon: '📅', title: '时间线', desc: '按时间顺序整理事件' },
];

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
                const typeInfo = GENERATE_TYPES.find(t => t.type === item.content_type);
                const itemEl = el('div', { className: 'generated-item' },
                    el('div', { className: 'generated-item-title' },
                        `${typeInfo?.icon || '📄'} ${item.title}`
                    ),
                    el('div', {
                        className: 'generated-item-meta',
                        style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
                    },
                        el('span', {}, item.created_at?.slice(0, 16).replace('T', ' ') || ''),
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
                    innerHTML: renderMarkdown(item.content),
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

    loadGenerated();
}
