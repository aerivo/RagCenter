from fastapi import APIRouter, status
from pydantic import BaseModel

api_v1_router = APIRouter(prefix="/api/v1")
knowledge_bases_router = APIRouter(prefix="/knowledge-bases", tags=["知识库"])
documents_router = APIRouter(prefix="/documents", tags=["文档"])
rag_router = APIRouter(prefix="/rag", tags=["检索"])


class PendingResponse(BaseModel):
    code: int = status.HTTP_501_NOT_IMPLEMENTED
    msg: str
    data: None = None


@knowledge_bases_router.post("/create", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def create_knowledge_base() -> PendingResponse:
    return PendingResponse(msg="知识库创建尚未接入")


@documents_router.post("/upload", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def upload_document() -> PendingResponse:
    return PendingResponse(msg="文档上传尚未接入")


@rag_router.post("/retrieve", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def retrieve() -> PendingResponse:
    return PendingResponse(msg="知识库检索尚未接入")


api_v1_router.include_router(knowledge_bases_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(rag_router)
