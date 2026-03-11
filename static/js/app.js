/**
 * Open Notebook — 应用入口 + 路由 + 状态管理
 */

import { renderHome } from './components/sidebar.js';
import { renderWorkspace } from './components/notebook.js';
import { renderSettings } from './components/settings.js';

// 全局状态
export const state = {
    currentNotebookId: null,
    notebooks: [],
};

/**
 * 路由处理
 */
function route() {
    const hash = location.hash || '#/';
    const main = document.getElementById('main-content');
    const title = document.getElementById('nav-title');

    if (hash === '#/settings') {
        title.textContent = '设置';
        renderSettings(main);
    } else if (hash.startsWith('#/notebook/')) {
        const id = hash.split('/')[2];
        state.currentNotebookId = id;
        renderWorkspace(main, id);
    } else {
        state.currentNotebookId = null;
        title.textContent = 'Open Notebook';
        renderHome(main);
    }
}

// 导航事件
document.getElementById('nav-home').addEventListener('click', () => {
    location.hash = '#/';
});

document.getElementById('nav-settings').addEventListener('click', () => {
    location.hash = '#/settings';
});

// 路由监听
window.addEventListener('hashchange', route);
window.addEventListener('load', route);
