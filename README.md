# Open Notebook

一个本地运行的 AI 笔记本应用，类似 Google NotebookLM。上传文档后可与 AI 对话、生成摘要、翻译等，所有数据存储在本地。

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 功能特性

- **文档管理** — 支持 PDF、TXT、Markdown、DOCX 格式上传，自动解析和分块
- **RAG 对话** — 基于文档内容的智能问答，检索增强生成，支持数学公式渲染（KaTeX）
- **内容生成** — 一键生成文档摘要、FAQ、学习指南、时间线
- **文档翻译** — 分段翻译长文档为中文，支持超时重试、跳过参考文献，可下载为 HTML（含公式和原文图片）
- **笔记保存** — 将 AI 回答保存为笔记，支持复制到剪贴板
- **灵活后端** — 兼容任意 OpenAI API 格式的 LLM（Ollama、OpenAI、MiniMax 等）
- **本地嵌入** — 默认使用本地 Sentence Transformers 模型，也支持 API 嵌入
- **纯浏览器前端** — 原生 HTML/JS/CSS，无需 Node.js 构建

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

复制配置模板并编辑：

```bash
cp config.example.toml config.toml
```

编辑 `config.toml`，配置 LLM 后端：

```toml
[llm]
# Ollama（本地）
base_url = "http://localhost:11434/v1"
api_key = ""
model = "qwen2.5:7b"

# 或 OpenAI
# base_url = "https://api.openai.com/v1"
# api_key = "sk-..."
# model = "gpt-4o-mini"

# 或 MiniMax
# base_url = "https://api.minimax.chat/v1"
# api_key = "sk-..."
# model = "MiniMax-M2.5"

[embedding]
provider = "local"
model = "paraphrase-multilingual-MiniLM-L12-v2"
```

### 3. 启动

```bash
python run.py
```

浏览器打开 `http://127.0.0.1:8000` 即可使用。

## 项目结构

```
open-notebook/
├── app/
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置加载（TOML）
│   ├── database.py          # SQLite 数据库初始化
│   ├── models.py            # Pydantic 数据模型
│   ├── routers/
│   │   ├── notebooks.py     # 笔记本 CRUD
│   │   ├── documents.py     # 文档上传/解析/图片提取
│   │   ├── chat.py          # RAG 对话（SSE 流式）
│   │   ├── generate.py      # 内容生成/翻译（分段+超时）
│   │   └── settings.py      # 设置管理
│   └── services/
│       ├── llm.py           # LLM 调用（OpenAI 兼容，think 标签过滤）
│       ├── document_parser.py  # PDF/DOCX/TXT 解析，图片提取
│       ├── chunker.py       # 文本分块
│       ├── embeddings.py    # 嵌入模型（本地/API）
│       ├── vector_store.py  # ChromaDB 向量存储
│       └── retriever.py     # 检索服务
├── static/
│   ├── index.html           # 主页面（含 KaTeX/marked CDN）
│   ├── css/style.css        # 样式
│   └── js/
│       ├── app.js           # 应用入口/路由
│       ├── api.js           # API 调用封装
│       ├── utils.js         # Markdown+KaTeX 渲染
│       └── components/      # UI 组件
├── config.example.toml      # 配置模板
├── requirements.txt         # Python 依赖
└── run.py                   # 启动脚本
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + Uvicorn |
| 数据库 | SQLite（WAL 模式） |
| 向量存储 | ChromaDB |
| 嵌入模型 | Sentence Transformers（本地）/ OpenAI API |
| LLM | 任意 OpenAI 兼容 API |
| 文档解析 | PyMuPDF（PDF）、python-docx（DOCX） |
| 前端 | 原生 HTML + ES Modules + CSS |
| 公式渲染 | KaTeX |
| Markdown | marked.js |

## 翻译功能说明

- 长文档自动按段落切分（每段约 6000 字），逐段调用 LLM 翻译
- **参考文献自动跳过** — 识别 References / Bibliography 部分，保留原文不翻译，节省时间和 token
- 附录（定理证明等）正常翻译
- 每个 token 60 秒超时保护，失败自动重试 2 次后跳过继续
- 下载的 HTML 文件包含 KaTeX 公式渲染和 PDF 原文图片（按页码位置内联）

## License

MIT
