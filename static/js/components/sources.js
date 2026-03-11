/**
 * 来源文档面板
 */

import { listDocuments, uploadDocument, deleteDocument } from '../api.js';
import { el, showToast, formatSize } from '../utils.js';

export function renderSources(panel, notebookId) {
    panel.innerHTML = '';

    const header = el('div', { className: 'panel-header' },
        el('h3', {}, '来源文档'),
    );
    panel.appendChild(header);

    const body = el('div', { className: 'panel-body' });

    // 上传区
    const uploadZone = el('div', { className: 'upload-zone' },
        el('div', { innerHTML: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>' }),
        el('div', {}, '拖放文件到此处，或点击上传'),
        el('div', { style: { fontSize: '11px', marginTop: '4px', color: 'var(--text-muted)' } }, '支持 PDF、TXT、Markdown、DOCX')
    );

    // 隐藏的 file input
    const fileInput = el('input', {
        type: 'file',
        accept: '.pdf,.txt,.md,.docx',
        style: { display: 'none' },
    });
    fileInput.multiple = true;
    body.appendChild(fileInput);

    uploadZone.addEventListener('click', () => fileInput.click());

    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });
    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });

    fileInput.addEventListener('change', () => {
        handleFiles(fileInput.files);
        fileInput.value = '';
    });

    async function handleFiles(files) {
        for (const file of files) {
            try {
                await uploadDocument(notebookId, file);
                showToast(`${file.name} 已上传`, 'success');
            } catch (e) {
                showToast(`${file.name}: ${e.message}`, 'error');
            }
        }
        loadDocuments();
    }

    body.appendChild(uploadZone);

    // 文档列表
    const docList = el('div', { className: 'doc-list' });
    body.appendChild(docList);

    panel.appendChild(body);

    let pollTimer = null;

    async function loadDocuments() {
        try {
            const { documents } = await listDocuments(notebookId);
            docList.innerHTML = '';

            if (documents.length === 0) {
                docList.appendChild(el('div', {
                    style: { textAlign: 'center', padding: '20px', color: 'var(--text-muted)', fontSize: '13px' },
                }, '暂无文档'));
                return;
            }

            let hasProcessing = false;

            for (const doc of documents) {
                if (doc.status === 'processing') hasProcessing = true;

                const statusClass = `status-${doc.status}`;
                const statusText = doc.status === 'processing' ? '处理中'
                    : doc.status === 'ready' ? `${doc.chunk_count} 块`
                    : '错误';

                const item = el('div', { className: 'doc-item' },
                    el('div', { className: `doc-item-icon ${doc.file_type}` }, doc.file_type.toUpperCase()),
                    el('div', { className: 'doc-item-info' },
                        el('div', { className: 'doc-item-name', title: doc.filename }, doc.filename),
                        el('div', { className: 'doc-item-meta' },
                            el('span', { className: `status-badge ${statusClass}` },
                                doc.status === 'processing' ? el('span', { className: 'spinner' }) : null,
                                statusText
                            ),
                            ' · ',
                            formatSize(doc.file_size)
                        )
                    ),
                    el('div', { className: 'doc-item-actions' },
                        el('button', {
                            className: 'btn-icon',
                            title: '删除',
                            onclick: async (e) => {
                                e.stopPropagation();
                                if (!confirm(`确定删除 ${doc.filename}？`)) return;
                                try {
                                    await deleteDocument(notebookId, doc.id);
                                    showToast('文档已删除', 'info');
                                    loadDocuments();
                                } catch (err) {
                                    showToast(err.message, 'error');
                                }
                            },
                            innerHTML: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>',
                        })
                    )
                );
                docList.appendChild(item);
            }

            // 轮询处理中的文档
            if (hasProcessing) {
                if (!pollTimer) {
                    pollTimer = setInterval(loadDocuments, 2000);
                }
            } else {
                if (pollTimer) {
                    clearInterval(pollTimer);
                    pollTimer = null;
                }
            }
        } catch (e) {
            docList.innerHTML = '';
            docList.appendChild(el('div', {
                style: { color: 'var(--danger)', fontSize: '13px', padding: '8px' },
            }, `加载失败: ${e.message}`));
        }
    }

    loadDocuments();

    // 面板销毁时清理定时器
    const observer = new MutationObserver(() => {
        if (!document.contains(panel)) {
            if (pollTimer) clearInterval(pollTimer);
            observer.disconnect();
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });
}
