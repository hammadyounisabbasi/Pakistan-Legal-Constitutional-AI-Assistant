from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.api.dependencies import get_catalog, get_rag_service
from backend.app.core.config import Settings, get_settings
from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.services.catalog import Catalog

router = APIRouter()


@router.get("/health")
def health(settings: Settings = Depends(get_settings)):
    return {"status": "ok", "service": settings.app_name, "environment": settings.app_env}


@router.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest):
    # Instantiate expensive retrieval resources only after request validation succeeds.
    return await get_rag_service().answer(payload.message, payload.history)


@router.get("/api/sources")
def list_sources(
    limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
    catalog: Catalog = Depends(get_catalog),
):
    return {"items": catalog.list(limit, offset), "total": catalog.count()}


@router.get("/api/sources/{document_id}")
def source_detail(document_id: str, catalog: Catalog = Depends(get_catalog)):
    source = catalog.get(document_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.get("/api/system/status")
def system_status(catalog: Catalog = Depends(get_catalog)):
    return {
        "status": "operational",
        "indexed_documents": catalog.count(),
        "knowledge_base_ready": catalog.count() > 0,
    }
