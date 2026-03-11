/**
 * 笔记本工作区 — 三栏布局 + 右侧可拖拽调宽
 */

import { getNotebook, updateNotebook } from '../api.js';
import { el, showToast } from '../utils.js';
import { renderSources } from './sources.js';
import { renderChat } from './chat.js';
import { renderGenerate, refreshGenerated } from './generate.js';

export async function renderWorkspace(container, notebookId) {
    container.innerHTML = '';

    // 加载笔记本信息
    let notebook;
    try {
        notebook = await getNotebook(notebookId);
    } catch (e) {
        container.appendChild(el('div', { className: 'empty-state' },
            el('p', {}, '笔记本不存在'),
            el('button', { className: 'btn btn-primary', onclick: () => { location.hash = '#/'; } }, '返回首页')
        ));
        return;
    }

    // 更新标题
    const navTitle = document.getElementById('nav-title');
    navTitle.textContent = notebook.title;
    navTitle.style.cursor = 'pointer';
    navTitle.onclick = () => {
        const input = prompt('修改笔记本标题', notebook.title);
        if (input && input !== notebook.title) {
            updateNotebook(notebookId, { title: input }).then((updated) => {
                notebook.title = updated.title;
                navTitle.textContent = updated.title;
            }).catch(e => showToast(e.message, 'error'));
        }
    };

    // 三栏布局
    const workspace = el('div', { className: 'workspace' });

    // 左：来源
    const leftPanel = el('div', { className: 'panel active' });
    renderSources(leftPanel, notebookId);

    // 中：对话（传入 onSaveNote 回调）
    const centerPanel = el('div', { className: 'panel chat-panel active' });
    renderChat(centerPanel, notebookId, {
        onNoteSaved() {
            // 刷新右侧生成内容列表
            refreshGenerated(notebookId);
        },
    });

    // 右：生成（可调宽）
    const rightPanel = el('div', { className: 'panel panel-right active' });
    renderGenerate(rightPanel, notebookId);
    // 拖拽手柄放在 renderGenerate 之后，避免被 innerHTML='' 清除
    const resizeHandle = el('div', { className: 'resize-handle' });
    rightPanel.insertBefore(resizeHandle, rightPanel.firstChild);

    // 拖拽调宽逻辑
    let startX, startWidth;
    resizeHandle.addEventListener('mousedown', (e) => {
        e.preventDefault();
        startX = e.clientX;
        startWidth = rightPanel.offsetWidth;
        resizeHandle.classList.add('dragging');

        const onMove = (e) => {
            const delta = startX - e.clientX; // 向左拖 = 变宽
            const newWidth = Math.min(600, Math.max(240, startWidth + delta));
            rightPanel.style.width = newWidth + 'px';
        };

        const onUp = () => {
            resizeHandle.classList.remove('dragging');
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
        };

        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
    });

    workspace.appendChild(leftPanel);
    workspace.appendChild(centerPanel);
    workspace.appendChild(rightPanel);
    container.appendChild(workspace);
}
