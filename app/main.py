"""FastAPI 应用入口"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import load_config
from app.database import init_db

# 全局配置与服务实例
config = None
vector_store = None
embedding_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化，关闭时清理"""
    global config, vector_store, embedding_service

    config = load_config()

    # 确保数据目录存在
    data_dir = Path(config.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "uploads").mkdir(exist_ok=True)
    (data_dir / "chroma").mkdir(exist_ok=True)

    # 初始化数据库
    init_db(config.data_dir)

    # 初始化向量存储
    from app.services.vector_store import VectorStore
    vector_store = VectorStore(str(data_dir / "chroma"))

    # 初始化嵌入服务
    from app.services.embeddings import create_embedding_service
    embedding_service = create_embedding_service(config)

    yield


app = FastAPI(title="Open Notebook", lifespan=lifespan)

# 挂载路由
from app.routers import notebooks, documents, chat, generate, settings  # noqa: E402

app.include_router(notebooks.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(generate.router, prefix="/api")
app.include_router(settings.router, prefix="/api")

# 挂载静态文件
static_dir = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(static_dir / "index.html"))
