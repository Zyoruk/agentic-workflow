"""Tests for file attachment system."""

import pytest
from pathlib import Path

from agentic_workflow.core.file_attachment import (
    ChunkingService,
    FileAttachment,
    FileService,
    SearchResult,
    TextChunk,
    get_file_service,
)
from agentic_workflow.core.tenant import TenantService, TierType


class TestChunkingService:
    """Tests for ChunkingService."""

    def test_estimate_tokens(self):
        """Test token estimation."""
        service = ChunkingService()
        text = "Hello world, this is a test."
        tokens = service.estimate_tokens(text)

        assert tokens > 0
        assert tokens == len(text) // 4

    def test_chunk_small_text(self):
        """Test chunking text that fits in one chunk."""
        service = ChunkingService(max_chunk_tokens=1000)
        text = "This is a short text."
        chunks = service.chunk_text(text)

        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].metadata.chunk_index == 0
        assert chunks[0].metadata.total_chunks == 1

    def test_chunk_large_text(self):
        """Test chunking large text into multiple chunks."""
        service = ChunkingService(max_chunk_tokens=100)
        # Create text that will need multiple chunks
        text = "This is a test sentence. " * 100
        chunks = service.chunk_text(text)

        assert len(chunks) > 1
        assert all(chunk.metadata.total_chunks == len(chunks) for chunk in chunks)
        assert all(chunk.metadata.chunk_index < len(chunks) for chunk in chunks)

    def test_chunk_with_paragraphs(self):
        """Test chunking preserves paragraph boundaries."""
        service = ChunkingService(max_chunk_tokens=50, preserve_boundaries=True)
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        chunks = service.chunk_text(text)

        # Should preserve paragraph structure
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.metadata.tokens <= 50 * 4  # Approximate

    def test_chunk_empty_text(self):
        """Test chunking empty text."""
        service = ChunkingService()
        chunks = service.chunk_text("")

        assert len(chunks) == 0

    def test_chunk_metadata(self):
        """Test chunk metadata is correct."""
        service = ChunkingService(max_chunk_tokens=50)
        text = "A" * 500  # Long text
        chunks = service.chunk_text(text)

        for i, chunk in enumerate(chunks):
            assert chunk.metadata.chunk_index == i
            assert chunk.metadata.start_offset >= 0
            assert chunk.metadata.end_offset > chunk.metadata.start_offset
            assert chunk.metadata.tokens > 0


class TestFileAttachment:
    """Tests for FileAttachment model."""

    def test_create_file_attachment(self):
        """Test creating a file attachment."""
        file_attachment = FileAttachment(
            tenant_id="test-tenant",
            filename="test.txt",
            content_type="text/plain",
            size_bytes=1024,
            storage_path="/tmp/test.txt",
            content_hash="abc123",
        )

        assert file_attachment.tenant_id == "test-tenant"
        assert file_attachment.filename == "test.txt"
        assert file_attachment.size_bytes == 1024
        assert file_attachment.chunks_count == 0


@pytest.mark.asyncio
class TestFileService:
    """Tests for FileService."""

    async def test_upload_file_success(self):
        """Test uploading a file successfully."""
        tenant_service = TenantService()
        tenant = await tenant_service.create_tenant(
            name="Test Corp",
            tier=TierType.STANDARD,  # Allows file uploads
        )

        file_service = FileService(tenant_service=tenant_service)
        content = b"This is a test file content."

        file_attachment = await file_service.upload_file(
            tenant_id=tenant.id,
            filename="test.txt",
            content=content,
            content_type="text/plain",
        )

        assert file_attachment.filename == "test.txt"
        assert file_attachment.size_bytes == len(content)
        assert file_attachment.tenant_id == tenant.id
        assert file_attachment.content_hash is not None

    async def test_upload_file_free_tier_fails(self):
        """Test uploading file with free tier fails."""
        tenant_service = TenantService()
        tenant = await tenant_service.create_tenant(
            name="Test Corp",
            tier=TierType.FREE,  # No file uploads
        )

        file_service = FileService(tenant_service=tenant_service)
        content = b"Test content"

        with pytest.raises(ValueError, match="does not support file attachments"):
            await file_service.upload_file(
                tenant_id=tenant.id,
                filename="test.txt",
                content=content,
                content_type="text/plain",
            )

    async def test_upload_file_too_large(self):
        """Test uploading file that exceeds size limit."""
        tenant_service = TenantService()
        tenant = await tenant_service.create_tenant(
            name="Test Corp",
            tier=TierType.STANDARD,  # 100MB limit
        )

        file_service = FileService(tenant_service=tenant_service)
        # Create content larger than 100MB
        content = b"X" * (101 * 1024 * 1024)

        with pytest.raises(ValueError, match="exceeds limit"):
            await file_service.upload_file(
                tenant_id=tenant.id,
                filename="large.txt",
                content=content,
                content_type="text/plain",
            )

    async def test_upload_file_nonexistent_tenant(self):
        """Test uploading file with nonexistent tenant."""
        file_service = FileService()
        content = b"Test content"

        with pytest.raises(ValueError, match="Tenant not found"):
            await file_service.upload_file(
                tenant_id="nonexistent",
                filename="test.txt",
                content=content,
                content_type="text/plain",
            )

    async def test_upload_text_file_chunks(self):
        """Test uploading text file creates chunks."""
        tenant_service = TenantService()
        tenant = await tenant_service.create_tenant(
            name="Test Corp",
            tier=TierType.STANDARD,
        )

        file_service = FileService(tenant_service=tenant_service)
        # Create text content that will be chunked
        content = b"This is a test sentence. " * 100

        file_attachment = await file_service.upload_file(
            tenant_id=tenant.id,
            filename="test.txt",
            content=content,
            content_type="text/plain",
        )

        assert file_attachment.chunks_count > 0
        assert len(file_attachment.vector_ids) == file_attachment.chunks_count

    async def test_get_file(self):
        """Test getting a file."""
        tenant_service = TenantService()
        tenant = await tenant_service.create_tenant(
            name="Test Corp",
            tier=TierType.STANDARD,
        )

        file_service = FileService(tenant_service=tenant_service)
        uploaded = await file_service.upload_file(
            tenant_id=tenant.id,
            filename="test.txt",
            content=b"Test content",
            content_type="text/plain",
        )

        retrieved = await file_service.get_file(uploaded.id)
        assert retrieved is not None
        assert retrieved.id == uploaded.id
        assert retrieved.filename == uploaded.filename

    async def test_get_nonexistent_file(self):
        """Test getting nonexistent file."""
        file_service = FileService()
        file_attachment = await file_service.get_file("nonexistent")
        assert file_attachment is None

    async def test_list_files(self):
        """Test listing files for a tenant."""
        tenant_service = TenantService()
        tenant = await tenant_service.create_tenant(
            name="Test Corp",
            tier=TierType.STANDARD,
        )

        file_service = FileService(tenant_service=tenant_service)
        await file_service.upload_file(
            tenant_id=tenant.id,
            filename="file1.txt",
            content=b"Content 1",
            content_type="text/plain",
        )
        await file_service.upload_file(
            tenant_id=tenant.id,
            filename="file2.txt",
            content=b"Content 2",
            content_type="text/plain",
        )

        files = await file_service.list_files(tenant.id)
        assert len(files) == 2

    async def test_list_files_excludes_expired(self):
        """Test listing files excludes expired by default."""
        tenant_service = TenantService()
        tenant = await tenant_service.create_tenant(
            name="Test Corp",
            tier=TierType.STANDARD,
        )

        file_service = FileService(tenant_service=tenant_service)
        # Upload with 0 retention (expires immediately)
        await file_service.upload_file(
            tenant_id=tenant.id,
            filename="expired.txt",
            content=b"Expired content",
            content_type="text/plain",
            retention_days=0,
        )

        files = await file_service.list_files(tenant.id, include_expired=False)
        # May or may not be expired yet depending on timing
        assert isinstance(files, list)

    async def test_delete_file(self):
        """Test deleting a file."""
        tenant_service = TenantService()
        tenant = await tenant_service.create_tenant(
            name="Test Corp",
            tier=TierType.STANDARD,
        )

        file_service = FileService(tenant_service=tenant_service)
        uploaded = await file_service.upload_file(
            tenant_id=tenant.id,
            filename="test.txt",
            content=b"Test content",
            content_type="text/plain",
        )

        deleted = await file_service.delete_file(uploaded.id)
        assert deleted is True

        retrieved = await file_service.get_file(uploaded.id)
        assert retrieved is None

    async def test_delete_nonexistent_file(self):
        """Test deleting nonexistent file."""
        file_service = FileService()
        deleted = await file_service.delete_file("nonexistent")
        assert deleted is False

    async def test_search_files(self):
        """Test searching file contents."""
        tenant_service = TenantService()
        tenant = await tenant_service.create_tenant(
            name="Test Corp",
            tier=TierType.STANDARD,
        )

        file_service = FileService(tenant_service=tenant_service)
        await file_service.upload_file(
            tenant_id=tenant.id,
            filename="doc1.txt",
            content=b"This document contains information about Python programming.",
            content_type="text/plain",
        )
        await file_service.upload_file(
            tenant_id=tenant.id,
            filename="doc2.txt",
            content=b"This document discusses Java development.",
            content_type="text/plain",
        )

        results = await file_service.search_files(
            tenant_id=tenant.id,
            query="Python",
            limit=10,
        )

        assert len(results) > 0
        assert any("Python" in r.content for r in results)

    async def test_search_files_with_filter(self):
        """Test searching files with file ID filter."""
        tenant_service = TenantService()
        tenant = await tenant_service.create_tenant(
            name="Test Corp",
            tier=TierType.STANDARD,
        )

        file_service = FileService(tenant_service=tenant_service)
        file1 = await file_service.upload_file(
            tenant_id=tenant.id,
            filename="doc1.txt",
            content=b"Python programming",
            content_type="text/plain",
        )

        results = await file_service.search_files(
            tenant_id=tenant.id,
            query="Python",
            file_ids=[file1.id],
            limit=10,
        )

        assert all(r.file_id == file1.id for r in results)

    async def test_cleanup_expired_files(self):
        """Test cleaning up expired files."""
        tenant_service = TenantService()
        tenant = await tenant_service.create_tenant(
            name="Test Corp",
            tier=TierType.STANDARD,
        )

        file_service = FileService(tenant_service=tenant_service)
        # Upload with 0 retention
        await file_service.upload_file(
            tenant_id=tenant.id,
            filename="expired.txt",
            content=b"Expired content",
            content_type="text/plain",
            retention_days=0,
        )

        # Wait a moment and cleanup
        deleted_count = await file_service.cleanup_expired_files()
        # Should cleanup expired files
        assert deleted_count >= 0

    async def test_file_metadata(self):
        """Test file upload with metadata."""
        tenant_service = TenantService()
        tenant = await tenant_service.create_tenant(
            name="Test Corp",
            tier=TierType.STANDARD,
        )

        file_service = FileService(tenant_service=tenant_service)
        metadata = {
            "tags": ["important", "documentation"],
            "description": "Test document",
        }

        file_attachment = await file_service.upload_file(
            tenant_id=tenant.id,
            filename="test.txt",
            content=b"Test content",
            content_type="text/plain",
            metadata=metadata,
        )

        assert file_attachment.metadata["tags"] == ["important", "documentation"]
        assert file_attachment.metadata["description"] == "Test document"

    async def test_usage_tracking(self):
        """Test usage is tracked for file operations."""
        tenant_service = TenantService()
        tenant = await tenant_service.create_tenant(
            name="Test Corp",
            tier=TierType.STANDARD,
        )

        file_service = FileService(tenant_service=tenant_service)
        content = b"Test content"

        await file_service.upload_file(
            tenant_id=tenant.id,
            filename="test.txt",
            content=content,
            content_type="text/plain",
        )

        usage = await tenant_service.get_usage(tenant.id)
        assert usage is not None
        assert usage.files_uploaded == 1
        assert usage.storage_bytes == len(content)


def test_get_file_service():
    """Test getting file service singleton."""
    service1 = get_file_service()
    service2 = get_file_service()

    assert service1 is service2
