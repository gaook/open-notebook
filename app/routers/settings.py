"""设置路由"""

from fastapi import APIRouter

from app.models import SettingsOut, SettingsUpdate
from app.config import save_config

router = APIRouter(tags=["settings"])


@router.get("/settings")
def get_settings():
    from app.main import config

    return SettingsOut(
        llm_base_url=config.llm_base_url,
        llm_model=config.llm_model,
        llm_api_key_set=bool(config.llm_api_key),
        embedding_provider=config.embedding_provider,
        embedding_model=config.embedding_model,
    )


@router.put("/settings")
def update_settings(body: SettingsUpdate):
    from app.main import config

    if body.llm_base_url is not None:
        config.llm_base_url = body.llm_base_url
    if body.llm_api_key is not None:
        config.llm_api_key = body.llm_api_key
    if body.llm_model is not None:
        config.llm_model = body.llm_model
    if body.embedding_provider is not None:
        config.embedding_provider = body.embedding_provider
    if body.embedding_model is not None:
        config.embedding_model = body.embedding_model

    save_config(config)
    return {"success": True}


@router.post("/settings/test")
async def test_connection():
    from app.main import config
    from app.services.llm import LLMService

    llm = LLMService(config.llm_base_url, config.llm_api_key, config.llm_model)
    result = await llm.test_connection()
    return result
