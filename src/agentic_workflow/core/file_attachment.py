"""
File attachment system with intelligent chunking and vector storage.

This module provides file upload, processing, chunking, and semantic search
capabilities following 2025 best practices.
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, BinaryIO
import tempfile
import os

from pydantic import BaseModel, Field

from .logging_config import get_logger
from .tenant import TenantService, get_tenant_service

logger = get_logger(__name__)


class ChunkMetadata(BaseModel):
    """Metadata for a text chunk."""

    chunk_index: int = Field(description="Index of this chunk in the document")
    total_chunks: int = Field(description="Total number of chunks in the document")
    start_offset: int = Field(description="Start character offset in original text")
    end_offset: int = Field(description="End character offset in original text")
    tokens: int = Field(description="Approximate token count for this chunk")


class TextChunk(BaseModel):
    """A chunk of text with metadata."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str = Field(description="Chunk text content")
    metadata: ChunkMetadata
    embedding_id: Optional[str] = Field(
        None, description="Vector store embedding ID"
    )


class FileAttachment(BaseModel):
    """File attachment model."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = Field(description="Tenant this file belongs to")
    filename: str = Field(description="Original filename")
    content_type: str = Field(description="MIME type")
    size_bytes: int = Field(description="File size in bytes")
    storage_path: str = Field(description="Path to stored file")
    content_hash: str = Field(description="SHA-256 hash of content")
    chunks_count: int = Field(default=0, description="Number of chunks created")
    vector_ids: List[str] = Field(
        default_factory=list, description="Vector store IDs for chunks"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = Field(
        None, description="Expiration timestamp"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    """Search result from file content."""

    file_id: str
    chunk_id: str
    content: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChunkingService:
    """Service for intelligent text chunking."""

    def __init__(
        self,
        max_chunk_tokens: int = 4000,
        overlap_tokens: int = 200,
        preserve_boundaries: bool = True,
    ):
        """Initialize chunking service.

        Args:
            max_chunk_tokens: Maximum tokens per chunk
            overlap_tokens: Overlap between chunks for context
            preserve_boundaries: Try to split at sentence/paragraph boundaries
        """
        self.max_chunk_tokens = max_chunk_tokens
        self.overlap_tokens = overlap_tokens
        self.preserve_boundaries = preserve_boundaries
        logger.info(
            f"ChunkingService initialized: max_tokens={max_chunk_tokens}, "
            f"overlap={overlap_tokens}"
        )

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Uses simple approximation: ~4 characters per token for English.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        return len(text) // 4

    def chunk_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[TextChunk]:
        """Chunk text with semantic boundary preservation.

        Args:
            text: Text to chunk
            metadata: Optional metadata to include

        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []

        # Estimate total tokens
        total_tokens = self.estimate_tokens(text)

        # If text is small enough, return as single chunk
        if total_tokens <= self.max_chunk_tokens:
            chunk_meta = ChunkMetadata(
                chunk_index=0,
                total_chunks=1,
                start_offset=0,
                end_offset=len(text),
                tokens=total_tokens,
            )
            return [
                TextChunk(
                    content=text,
                    metadata=chunk_meta,
                )
            ]

        # Split text into chunks
        chunks: List[TextChunk] = []
        
        if self.preserve_boundaries:
            # Split by paragraphs first, then sentences if needed
            paragraphs = text.split('\n\n')
            chunks = self._chunk_with_boundaries(paragraphs, metadata)
        else:
            # Simple fixed-size chunking
            chunks = self._chunk_fixed_size(text, metadata)

        logger.debug(f"Created {len(chunks)} chunks from {total_tokens} tokens")
        return chunks

    def _chunk_with_boundaries(
        self,
        paragraphs: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[TextChunk]:
        """Chunk text preserving paragraph boundaries.

        Args:
            paragraphs: List of paragraphs
            metadata: Optional metadata

        Returns:
            List of text chunks
        """
        chunks: List[TextChunk] = []
        current_chunk = []
        current_tokens = 0
        current_offset = 0

        for para in paragraphs:
            para_tokens = self.estimate_tokens(para)

            # If single paragraph is too large, split it
            if para_tokens > self.max_chunk_tokens:
                # Save current chunk if not empty
                if current_chunk:
                    chunk_text = '\n\n'.join(current_chunk)
                    chunks.append(
                        self._create_chunk(
                            chunk_text,
                            len(chunks),
                            current_offset,
                            current_offset + len(chunk_text),
                            current_tokens,
                        )
                    )
                    current_chunk = []
                    current_tokens = 0
                    current_offset += len(chunk_text) + 2  # +2 for \n\n

                # Split large paragraph by sentences
                sentences = para.split('. ')
                for sentence in sentences:
                    sent_tokens = self.estimate_tokens(sentence)
                    
                    if current_tokens + sent_tokens > self.max_chunk_tokens:
                        if current_chunk:
                            chunk_text = '. '.join(current_chunk)
                            chunks.append(
                                self._create_chunk(
                                    chunk_text,
                                    len(chunks),
                                    current_offset,
                                    current_offset + len(chunk_text),
                                    current_tokens,
                                )
                            )
                            current_offset += len(chunk_text) + 2
                        current_chunk = [sentence]
                        current_tokens = sent_tokens
                    else:
                        current_chunk.append(sentence)
                        current_tokens += sent_tokens

            # Add paragraph to current chunk
            elif current_tokens + para_tokens > self.max_chunk_tokens:
                # Save current chunk
                if current_chunk:
                    chunk_text = '\n\n'.join(current_chunk)
                    chunks.append(
                        self._create_chunk(
                            chunk_text,
                            len(chunks),
                            current_offset,
                            current_offset + len(chunk_text),
                            current_tokens,
                        )
                    )
                    current_offset += len(chunk_text) + 2

                # Start new chunk with this paragraph
                current_chunk = [para]
                current_tokens = para_tokens
            else:
                current_chunk.append(para)
                current_tokens += para_tokens

        # Add final chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            chunks.append(
                self._create_chunk(
                    chunk_text,
                    len(chunks),
                    current_offset,
                    current_offset + len(chunk_text),
                    current_tokens,
                )
            )

        # Update total chunks count
        for chunk in chunks:
            chunk.metadata.total_chunks = len(chunks)

        return chunks

    def _chunk_fixed_size(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[TextChunk]:
        """Chunk text with fixed size (fallback method).

        Args:
            text: Text to chunk
            metadata: Optional metadata

        Returns:
            List of text chunks
        """
        chunks: List[TextChunk] = []
        chunk_size = self.max_chunk_tokens * 4  # Approximate characters
        overlap = self.overlap_tokens * 4

        offset = 0
        chunk_index = 0

        while offset < len(text):
            end = min(offset + chunk_size, len(text))
            chunk_text = text[offset:end]
            
            chunks.append(
                self._create_chunk(
                    chunk_text,
                    chunk_index,
                    offset,
                    end,
                    self.estimate_tokens(chunk_text),
                )
            )

            offset += chunk_size - overlap
            chunk_index += 1

        # Update total chunks count
        for chunk in chunks:
            chunk.metadata.total_chunks = len(chunks)

        return chunks

    def _create_chunk(
        self,
        content: str,
        index: int,
        start: int,
        end: int,
        tokens: int,
    ) -> TextChunk:
        """Create a text chunk with metadata.

        Args:
            content: Chunk content
            index: Chunk index
            start: Start offset
            end: End offset
            tokens: Token count

        Returns:
            TextChunk instance
        """
        return TextChunk(
            content=content,
            metadata=ChunkMetadata(
                chunk_index=index,
                total_chunks=0,  # Will be updated later
                start_offset=start,
                end_offset=end,
                tokens=tokens,
            ),
        )


class FileService:
    """Service for file attachment management."""

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        tenant_service: Optional[TenantService] = None,
    ):
        """Initialize file service.

        Args:
            storage_dir: Directory for file storage
            tenant_service: Tenant service instance
        """
        self.storage_dir = Path(storage_dir or tempfile.gettempdir()) / "file_attachments"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.tenant_service = tenant_service or get_tenant_service()
        self.chunking_service = ChunkingService()
        
        # In-memory storage for MVP (replace with database)
        self._files: Dict[str, FileAttachment] = {}
        self._chunks: Dict[str, List[TextChunk]] = {}
        
        logger.info(f"FileService initialized: storage={self.storage_dir}")

    def _calculate_hash(self, content: bytes) -> str:
        """Calculate SHA-256 hash of content.

        Args:
            content: File content

        Returns:
            Hex digest of SHA-256 hash
        """
        return hashlib.sha256(content).hexdigest()

    def _get_storage_path(self, tenant_id: str, file_id: str) -> Path:
        """Get storage path for a file.

        Args:
            tenant_id: Tenant ID
            file_id: File ID

        Returns:
            Path to file storage location
        """
        tenant_dir = self.storage_dir / tenant_id
        tenant_dir.mkdir(exist_ok=True)
        return tenant_dir / file_id

    async def upload_file(
        self,
        tenant_id: str,
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, Any]] = None,
        retention_days: Optional[int] = None,
    ) -> FileAttachment:
        """Upload and process a file attachment.

        Args:
            tenant_id: Tenant ID
            filename: Original filename
            content: File content
            content_type: MIME type
            metadata: Optional metadata
            retention_days: Days to retain file (uses tier default if not specified)

        Returns:
            Created file attachment

        Raises:
            ValueError: If tenant not found or file too large
        """
        # Validate tenant and tier limits
        tenant = await self.tenant_service.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant not found: {tenant_id}")

        limits = tenant.get_limits()
        if not limits.file_attachments:
            raise ValueError(
                f"Tenant tier '{tenant.tier}' does not support file attachments"
            )

        size_mb = len(content) / (1024 * 1024)
        if size_mb > limits.max_file_size_mb:
            raise ValueError(
                f"File size ({size_mb:.2f}MB) exceeds limit ({limits.max_file_size_mb}MB)"
            )

        # Create file attachment
        file_id = str(uuid.uuid4())
        storage_path = self._get_storage_path(tenant_id, file_id)
        content_hash = self._calculate_hash(content)

        # Calculate expiration
        expires_at = None
        if retention_days is None:
            retention_days = limits.storage_days
        if retention_days > 0:
            expires_at = datetime.now(timezone.utc) + timedelta(days=retention_days)

        file_attachment = FileAttachment(
            id=file_id,
            tenant_id=tenant_id,
            filename=filename,
            content_type=content_type,
            size_bytes=len(content),
            storage_path=str(storage_path),
            content_hash=content_hash,
            expires_at=expires_at,
            metadata=metadata or {},
        )

        # Save file to disk
        storage_path.write_bytes(content)

        # Chunk and store
        text_content = self._extract_text(content, content_type)
        if text_content:
            chunks = await self._chunk_and_store(file_id, text_content)
            file_attachment.chunks_count = len(chunks)
            file_attachment.vector_ids = [c.embedding_id or "" for c in chunks]

        # Store attachment
        self._files[file_id] = file_attachment

        # Track usage
        await self.tenant_service.track_usage(
            tenant_id,
            files=1,
            storage_bytes=len(content),
        )

        logger.info(
            f"Uploaded file {file_id} for tenant {tenant_id}: "
            f"{filename} ({size_mb:.2f}MB, {file_attachment.chunks_count} chunks)"
        )
        return file_attachment

    def _extract_text(self, content: bytes, content_type: str) -> str:
        """Extract text from file content.

        Args:
            content: File content
            content_type: MIME type

        Returns:
            Extracted text
        """
        # For MVP, only handle text files
        if content_type.startswith("text/"):
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                logger.warning("Failed to decode text file")
                return ""
        
        # TODO: Add support for PDF, DOCX, etc.
        logger.debug(f"Unsupported content type for text extraction: {content_type}")
        return ""

    async def _chunk_and_store(
        self, file_id: str, text: str
    ) -> List[TextChunk]:
        """Chunk text and store in vector database.

        Args:
            file_id: File ID
            text: Text content

        Returns:
            List of created chunks
        """
        chunks = self.chunking_service.chunk_text(text)
        
        # Store chunks (in production, this would store embeddings in Weaviate)
        self._chunks[file_id] = chunks
        
        # Generate mock embedding IDs for MVP
        for i, chunk in enumerate(chunks):
            chunk.embedding_id = f"{file_id}_chunk_{i}"

        logger.debug(f"Created {len(chunks)} chunks for file {file_id}")
        return chunks

    async def get_file(self, file_id: str) -> Optional[FileAttachment]:
        """Get file attachment by ID.

        Args:
            file_id: File ID

        Returns:
            File attachment if found, None otherwise
        """
        return self._files.get(file_id)

    async def list_files(
        self,
        tenant_id: str,
        include_expired: bool = False,
    ) -> List[FileAttachment]:
        """List files for a tenant.

        Args:
            tenant_id: Tenant ID
            include_expired: Whether to include expired files

        Returns:
            List of file attachments
        """
        files = [f for f in self._files.values() if f.tenant_id == tenant_id]

        if not include_expired:
            now = datetime.now(timezone.utc)
            files = [
                f for f in files
                if f.expires_at is None or f.expires_at > now
            ]

        return files

    async def delete_file(self, file_id: str) -> bool:
        """Delete a file attachment.

        Args:
            file_id: File ID

        Returns:
            True if deleted, False if not found
        """
        file_attachment = self._files.get(file_id)
        if not file_attachment:
            return False

        # Delete from disk
        storage_path = Path(file_attachment.storage_path)
        if storage_path.exists():
            storage_path.unlink()

        # Delete chunks
        if file_id in self._chunks:
            del self._chunks[file_id]

        # Delete attachment record
        del self._files[file_id]

        # Update usage
        await self.tenant_service.track_usage(
            file_attachment.tenant_id,
            files=-1,
            storage_bytes=-file_attachment.size_bytes,
        )

        logger.info(f"Deleted file {file_id}")
        return True

    async def search_files(
        self,
        tenant_id: str,
        query: str,
        file_ids: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[SearchResult]:
        """Search file contents using semantic similarity.

        Args:
            tenant_id: Tenant ID
            query: Search query
            file_ids: Optional list of file IDs to search within
            limit: Maximum results to return

        Returns:
            List of search results
        """
        # For MVP, use simple keyword matching
        # In production, this would use Weaviate vector search
        results: List[SearchResult] = []

        files_to_search = [
            f for f in self._files.values()
            if f.tenant_id == tenant_id
            and (not file_ids or f.id in file_ids)
        ]

        query_lower = query.lower()

        for file_attachment in files_to_search:
            if file_attachment.id not in self._chunks:
                continue

            for chunk in self._chunks[file_attachment.id]:
                if query_lower in chunk.content.lower():
                    # Calculate simple similarity score
                    score = min(
                        chunk.content.lower().count(query_lower) * 0.1,
                        1.0
                    )
                    
                    results.append(
                        SearchResult(
                            file_id=file_attachment.id,
                            chunk_id=chunk.id,
                            content=chunk.content,
                            similarity_score=score,
                            metadata={
                                "filename": file_attachment.filename,
                                "chunk_index": chunk.metadata.chunk_index,
                                "total_chunks": chunk.metadata.total_chunks,
                            },
                        )
                    )

        # Sort by similarity score and limit
        results.sort(key=lambda r: r.similarity_score, reverse=True)
        return results[:limit]

    async def cleanup_expired_files(self) -> int:
        """Remove expired file attachments.

        Returns:
            Number of files deleted
        """
        now = datetime.now(timezone.utc)
        expired_files = [
            f for f in self._files.values()
            if f.expires_at and f.expires_at <= now
        ]

        count = 0
        for file_attachment in expired_files:
            if await self.delete_file(file_attachment.id):
                count += 1

        if count > 0:
            logger.info(f"Cleaned up {count} expired files")

        return count


# Global file service instance
_file_service: Optional[FileService] = None


def get_file_service() -> FileService:
    """Get or create the global file service instance.

    Returns:
        FileService instance
    """
    global _file_service
    if _file_service is None:
        _file_service = FileService()
    return _file_service
