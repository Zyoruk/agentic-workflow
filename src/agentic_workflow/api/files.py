"""
File attachment API endpoints.

This module provides REST API endpoints for file upload, management,
and semantic search functionality.
"""

from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field

from agentic_workflow.core.file_attachment import (
    FileService,
    get_file_service,
)
from agentic_workflow.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/files", tags=["files"])


# Request/Response Models

class FileUploadResponse(BaseModel):
    """Response model for file upload."""

    file_id: str
    filename: str
    content_type: str
    size_bytes: int
    chunks_count: int
    vector_ids: List[str]
    expires_at: Optional[str]
    created_at: str


class FileDetailsResponse(BaseModel):
    """Response model for file details."""

    id: str
    tenant_id: str
    filename: str
    content_type: str
    size_bytes: int
    content_hash: str
    chunks_count: int
    vector_ids: List[str]
    created_at: str
    expires_at: Optional[str]
    metadata: Dict[str, Any]


class SearchRequest(BaseModel):
    """Request model for file search."""

    query: str = Field(..., min_length=1)
    file_ids: Optional[List[str]] = Field(None, description="Optional file ID filter")
    limit: int = Field(default=10, ge=1, le=100)


class SearchResultResponse(BaseModel):
    """Response model for search results."""

    file_id: str
    chunk_id: str
    content: str
    similarity_score: float
    metadata: Dict[str, Any]


class SearchResponse(BaseModel):
    """Response model for search operation."""

    query: str
    results: List[SearchResultResponse]
    total_results: int


# Endpoints

@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_file(
    tenant_id: str = Form(...),
    file: UploadFile = File(...),
    retention_days: Optional[int] = Form(None),
    tags: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
) -> Dict[str, Any]:
    """Upload a file attachment.

    Args:
        tenant_id: Tenant ID
        file: File to upload
        retention_days: Optional retention period (uses tier default if not specified)
        tags: Optional comma-separated tags
        description: Optional file description

    Returns:
        File attachment details
    """
    try:
        file_service = get_file_service()

        # Prepare metadata
        metadata: Dict[str, Any] = {}
        if tags:
            metadata["tags"] = [t.strip() for t in tags.split(",")]
        if description:
            metadata["description"] = description

        # Read file content
        content = await file.read()

        # Upload and process file
        file_attachment = await file_service.upload_file(
            tenant_id=tenant_id,
            filename=file.filename or "unnamed",
            content=content,
            content_type=file.content_type or "application/octet-stream",
            metadata=metadata,
            retention_days=retention_days,
        )

        return {
            "file_id": file_attachment.id,
            "filename": file_attachment.filename,
            "content_type": file_attachment.content_type,
            "size_bytes": file_attachment.size_bytes,
            "chunks_count": file_attachment.chunks_count,
            "vector_ids": file_attachment.vector_ids,
            "expires_at": (
                file_attachment.expires_at.isoformat()
                if file_attachment.expires_at
                else None
            ),
            "created_at": file_attachment.created_at.isoformat(),
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file",
        )


@router.get("/", response_model=List[FileDetailsResponse])
async def list_files(
    tenant_id: str,
    include_expired: bool = False,
) -> List[Dict[str, Any]]:
    """List files for a tenant.

    Args:
        tenant_id: Tenant ID
        include_expired: Whether to include expired files

    Returns:
        List of file attachments
    """
    try:
        file_service = get_file_service()
        files = await file_service.list_files(
            tenant_id=tenant_id,
            include_expired=include_expired,
        )

        return [
            {
                "id": f.id,
                "tenant_id": f.tenant_id,
                "filename": f.filename,
                "content_type": f.content_type,
                "size_bytes": f.size_bytes,
                "content_hash": f.content_hash,
                "chunks_count": f.chunks_count,
                "vector_ids": f.vector_ids,
                "created_at": f.created_at.isoformat(),
                "expires_at": f.expires_at.isoformat() if f.expires_at else None,
                "metadata": f.metadata,
            }
            for f in files
        ]

    except Exception as e:
        logger.error(f"Failed to list files for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list files",
        )


@router.get("/{file_id}", response_model=FileDetailsResponse)
async def get_file(file_id: str) -> Dict[str, Any]:
    """Get file details by ID.

    Args:
        file_id: File ID

    Returns:
        File attachment details
    """
    try:
        file_service = get_file_service()
        file_attachment = await file_service.get_file(file_id)

        if not file_attachment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_id}",
            )

        return {
            "id": file_attachment.id,
            "tenant_id": file_attachment.tenant_id,
            "filename": file_attachment.filename,
            "content_type": file_attachment.content_type,
            "size_bytes": file_attachment.size_bytes,
            "content_hash": file_attachment.content_hash,
            "chunks_count": file_attachment.chunks_count,
            "vector_ids": file_attachment.vector_ids,
            "created_at": file_attachment.created_at.isoformat(),
            "expires_at": (
                file_attachment.expires_at.isoformat()
                if file_attachment.expires_at
                else None
            ),
            "metadata": file_attachment.metadata,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get file",
        )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(file_id: str) -> None:
    """Delete a file attachment.

    Args:
        file_id: File ID
    """
    try:
        file_service = get_file_service()
        deleted = await file_service.delete_file(file_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_id}",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete file {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file",
        )


@router.post("/search", response_model=SearchResponse)
async def search_files(
    tenant_id: str,
    request: SearchRequest,
) -> Dict[str, Any]:
    """Search file contents using semantic similarity.

    Args:
        tenant_id: Tenant ID
        request: Search request with query and filters

    Returns:
        Search results
    """
    try:
        file_service = get_file_service()
        results = await file_service.search_files(
            tenant_id=tenant_id,
            query=request.query,
            file_ids=request.file_ids,
            limit=request.limit,
        )

        return {
            "query": request.query,
            "results": [
                {
                    "file_id": r.file_id,
                    "chunk_id": r.chunk_id,
                    "content": r.content,
                    "similarity_score": r.similarity_score,
                    "metadata": r.metadata,
                }
                for r in results
            ],
            "total_results": len(results),
        }

    except Exception as e:
        logger.error(f"Failed to search files for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search files",
        )


@router.post("/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_expired_files() -> Dict[str, Any]:
    """Cleanup expired file attachments.

    Returns:
        Number of files deleted
    """
    try:
        file_service = get_file_service()
        deleted_count = await file_service.cleanup_expired_files()

        return {
            "deleted_count": deleted_count,
            "message": f"Cleaned up {deleted_count} expired files",
        }

    except Exception as e:
        logger.error(f"Failed to cleanup expired files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup expired files",
        )


@router.get("/{file_id}/stats", status_code=status.HTTP_200_OK)
async def get_file_stats(file_id: str) -> Dict[str, Any]:
    """Get statistics for a file.

    Args:
        file_id: File ID

    Returns:
        File statistics
    """
    try:
        file_service = get_file_service()
        file_attachment = await file_service.get_file(file_id)

        if not file_attachment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_id}",
            )

        # Calculate stats
        size_mb = file_attachment.size_bytes / (1024 * 1024)
        avg_chunk_size = (
            file_attachment.size_bytes / file_attachment.chunks_count
            if file_attachment.chunks_count > 0
            else 0
        )

        return {
            "file_id": file_attachment.id,
            "filename": file_attachment.filename,
            "size_bytes": file_attachment.size_bytes,
            "size_mb": round(size_mb, 2),
            "chunks_count": file_attachment.chunks_count,
            "avg_chunk_size_bytes": round(avg_chunk_size, 2),
            "content_hash": file_attachment.content_hash,
            "age_days": (
                (file_attachment.created_at - file_attachment.created_at).days
                if file_attachment.created_at
                else 0
            ),
            "expires_in_days": (
                (file_attachment.expires_at - file_attachment.created_at).days
                if file_attachment.expires_at
                else None
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file stats for {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get file stats",
        )
