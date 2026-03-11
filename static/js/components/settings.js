/**
 * 设置页面
 */

import { el, showToast } from '../utils.js';

export async function renderSettings(container) {
    container.innerHTML = '';

    const page = el('div', { className: 'settings-page' });
    page.appendChild(el('h2', {}, '设置'));

    // 加载当前配置
    let settings = {};
    try {
        const resp = await fetch('/api/settings');
        if (resp.ok) settings = await resp.json();
    } catch (e) { /* 使用默认值 */ }

    // LLM 设置
    const llmSection = el('div', { className: 'settings-section' });
    llmSection.appendChild(el('h3', {}, '大语言模型 (LLM)'));

    const baseUrlInput = createInput('API 地址', 'llm_base_url',
        settings.llm_base_url || 'http://localhost:11434/v1',
        '例如: http://localhost:11434/v1 (Ollama)');

    const apiKeyInput = createInput('API Key', 'llm_api_key', '',
        settings.llm_api_key_set ? '(已设置，留空保持不变)' : '可选，Ollama 不需要',
        'password');

    const modelInput = createInput('模型名称', 'llm_model',
        settings.llm_model || 'qwen2.5:7b',
        '例如: qwen2.5:7b, gpt-4o-mini');

    llmSection.appendChild(baseUrlInput);
    llmSection.appendChild(apiKeyInput);
    llmSection.appendChild(modelInput);

    // 测试连接按钮
    const testBtn = el('button', {
        className: 'btn btn-secondary',
        onclick: async () => {
            testBtn.disabled = true;
            testBtn.textContent = '测试中...';
            try {
                const resp = await fetch('/api/settings/test', { method: 'POST' });
                const result = await resp.json();
                if (result.success) {
                    showToast('连接成功', 'success');
                } else {
                    showToast(result.message || '连接失败', 'error');
                }
            } catch (e) {
                showToast(`测试失败: ${e.message}`, 'error');
            }
            testBtn.disabled = false;
            testBtn.textContent = '测试连接';
        },
    }, '测试连接');

    llmSection.appendChild(el('div', { className: 'settings-actions' }, testBtn));
    page.appendChild(llmSection);

    // 嵌入模型设置
    const embSection = el('div', { className: 'settings-section' });
    embSection.appendChild(el('h3', {}, '嵌入模型'));

    const embProviderSelect = createSelect('嵌入方式', 'emb_provider', [
        { value: 'local', label: '本地模型 (sentence-transformers)' },
        { value: 'api', label: 'API 嵌入' },
    ], settings.embedding_provider || 'local');

    const embModelInput = createInput('模型名称', 'emb_model',
        settings.embedding_model || 'paraphrase-multilingual-MiniLM-L12-v2',
        '本地: paraphrase-multilingual-MiniLM-L12-v2');

    embSection.appendChild(embProviderSelect);
    embSection.appendChild(embModelInput);
    page.appendChild(embSection);

    // 保存按钮
    const saveBtn = el('button', {
        className: 'btn btn-primary',
        onclick: async () => {
            saveBtn.disabled = true;
            saveBtn.textContent = '保存中...';
            try {
                const data = {
                    llm_base_url: page.querySelector('[name="llm_base_url"]').value,
                    llm_model: page.querySelector('[name="llm_model"]').value,
                    embedding_provider: page.querySelector('[name="emb_provider"]').value,
                    embedding_model: page.querySelector('[name="emb_model"]').value,
                };
                const apiKey = page.querySelector('[name="llm_api_key"]').value;
                if (apiKey) data.llm_api_key = apiKey;

                const resp = await fetch('/api/settings', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data),
                });
                if (resp.ok) {
                    showToast('设置已保存，重启服务后生效', 'success');
                } else {
                    const err = await resp.json();
                    showToast(err.detail || '保存失败', 'error');
                }
            } catch (e) {
                showToast(e.message, 'error');
            }
            saveBtn.disabled = false;
            saveBtn.textContent = '保存设置';
        },
    }, '保存设置');

    page.appendChild(el('div', { className: 'settings-actions', style: { marginTop: '8px' } }, saveBtn));

    container.appendChild(page);
}

function createInput(label, name, value, placeholder = '', type = 'text') {
    const group = el('div', { className: 'form-group' });
    group.appendChild(el('label', {}, label));
    const input = el('input', { type, name, value, placeholder });
    group.appendChild(input);
    return group;
}

function createSelect(label, name, options, selectedValue) {
    const group = el('div', { className: 'form-group' });
    group.appendChild(el('label', {}, label));
    const select = el('select', { name });
    for (const opt of options) {
        const option = el('option', { value: opt.value }, opt.label);
        if (opt.value === selectedValue) option.selected = true;
        select.appendChild(option);
    }
    group.appendChild(select);
    return group;
}
