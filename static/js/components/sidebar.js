/**
 * 首页 — 笔记本列表
 */

import { listNotebooks, createNotebook, deleteNotebook } from '../api.js';
import { el, showToast, formatTime } from '../utils.js';

export async function renderHome(container) {
    container.innerHTML = '';

    const page = el('div', { className: 'home-page' });

    const header = el('div', { className: 'home-header' },
        el('h2', {}, '我的笔记本'),
        el('button', {
            className: 'btn btn-primary',
            onclick: async () => {
                try {
                    const nb = await createNotebook();
                    location.hash = `#/notebook/${nb.id}`;
                } catch (e) {
                    showToast(e.message, 'error');
                }
            },
        },
            el('span', {}, '+ 新建笔记本')
        )
    );
    page.appendChild(header);

    // 加载笔记本列表
    try {
        const { notebooks } = await listNotebooks();

        if (notebooks.length === 0) {
            const empty = el('div', { className: 'empty-state' },
                el('div', { innerHTML: '<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>' }),
                el('p', {}, '还没有笔记本'),
                el('p', { style: { fontSize: '13px' } }, '点击上方按钮创建你的第一个笔记本')
            );
            page.appendChild(empty);
        } else {
            const grid = el('div', { className: 'notebook-grid' });
            for (const nb of notebooks) {
                const card = el('div', {
                    className: 'notebook-card',
                    onclick: () => { location.hash = `#/notebook/${nb.id}`; },
                },
                    el('div', { className: 'notebook-card-title' },
                        el('span', {}, '📓'),
                        el('span', {}, nb.title)
                    ),
                    el('div', { className: 'notebook-card-desc' }, nb.description || '暂无描述'),
                    el('div', { className: 'notebook-card-meta' },
                        el('span', {}, `${nb.doc_count} 个文档`),
                        el('span', {}, `${nb.message_count} 条消息`),
                        el('span', {}, formatTime(nb.updated_at))
                    )
                );
                grid.appendChild(card);
            }
            page.appendChild(grid);
        }
    } catch (e) {
        page.appendChild(el('div', { className: 'empty-state' },
            el('p', {}, `加载失败: ${e.message}`)
        ));
    }

    container.appendChild(page);
}
