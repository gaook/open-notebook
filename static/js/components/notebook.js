/**
 * 笔记本工作区 — 三栏布局
 */

import { getNotebook, updateNotebook } from '../api.js';
import { el, showToast } from '../utils.js';
import { renderSources } from './sources.js';
import { renderChat } from './chat.js';
import { renderGenerate } from './generate.js';

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

    // 中：对话
    const centerPanel = el('div', { className: 'panel chat-panel active' });
    renderChat(centerPanel, notebookId);

    // 右：生成
    const rightPanel = el('div', { className: 'panel active' });
    renderGenerate(rightPanel, notebookId);

    workspace.appendChild(leftPanel);
    workspace.appendChild(centerPanel);
    workspace.appendChild(rightPanel);
    container.appendChild(workspace);
}
