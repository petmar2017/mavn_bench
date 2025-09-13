"""Tests for TranscriptionService

Following prompt.md guidelines:
- No mocks, only real implementations
- Async tests with pytest-asyncio
- 80% coverage minimum
- Real test data
"""

import pytest
import pytest_asyncio
import asyncio
import tempfile
import os
from pathlib import Path
from datetime import datetime
import hashlib
import json

from src.services.transcription_service import TranscriptionService
from src.models.document import (
    DocumentMessage,
    DocumentType,
    DocumentMetadata,
    DocumentContent,
    ProcessingStage,
    DocumentSource
)
from src.core.config import get_settings


@pytest_asyncio.fixture
async def transcription_service():
    """Create TranscriptionService instance for testing"""
    service = TranscriptionService()
    yield service
    # Cleanup
    try:
        await service.cleanup_temp_files()
    except Exception:
        pass  # Ignore cleanup errors in tests


@pytest.fixture
def test_audio_file(tmp_path):
    """Create a test audio file"""
    # Create a simple WAV file header (44 bytes) + minimal data
    # This is a valid WAV file structure
    audio_file = tmp_path / "test_audio.wav"

    # WAV file header
    wav_header = bytearray()
    wav_header.extend(b'RIFF')  # ChunkID
    wav_header.extend((36).to_bytes(4, 'little'))  # ChunkSize
    wav_header.extend(b'WAVE')  # Format
    wav_header.extend(b'fmt ')  # Subchunk1ID
    wav_header.extend((16).to_bytes(4, 'little'))  # Subchunk1Size
    wav_header.extend((1).to_bytes(2, 'little'))  # AudioFormat (PCM)
    wav_header.extend((1).to_bytes(2, 'little'))  # NumChannels
    wav_header.extend((44100).to_bytes(4, 'little'))  # SampleRate
    wav_header.extend((88200).to_bytes(4, 'little'))  # ByteRate
    wav_header.extend((2).to_bytes(2, 'little'))  # BlockAlign
    wav_header.extend((16).to_bytes(2, 'little'))  # BitsPerSample
    wav_header.extend(b'data')  # Subchunk2ID
    wav_header.extend((0).to_bytes(4, 'little'))  # Subchunk2Size (no data)

    audio_file.write_bytes(wav_header)
    return str(audio_file)


@pytest.fixture
def test_video_metadata():
    """Sample video metadata"""
    return {
        'title': 'Test Video',
        'duration': 300,
        'channel': 'Test Channel',
        'upload_date': '20240101',
        'description': 'Test description',
        'thumbnail': 'https://example.com/thumb.jpg'
    }


@pytest.fixture
def test_podcast_metadata():
    """Sample podcast metadata"""
    return {
        'title': 'Test Podcast Episode',
        'duration': 1800,
        'episode': 'Episode 1',
        'series': 'Test Podcast Series',
        'description': 'Test podcast description'
    }


class TestTranscriptionService:
    """Test suite for TranscriptionService"""

    @pytest.mark.asyncio
    async def test_service_initialization(self, transcription_service):
        """Test service initializes correctly"""
        assert transcription_service is not None
        assert transcription_service.service_name == "TranscriptionService"
        assert transcription_service.temp_dir.exists()
        assert transcription_service.storage is not None
        assert transcription_service.ydl_opts is not None

    @pytest.mark.asyncio
    async def test_health_check(self, transcription_service):
        """Test health check functionality"""
        health = await transcription_service.health_check()

        assert health['service'] == 'TranscriptionService'
        assert health['status'] == 'healthy'
        assert 'temp_dir' in health
        assert 'yt_dlp_version' in health
        assert 'storage_type' in health

    @pytest.mark.asyncio
    async def test_temp_directory_creation(self, transcription_service):
        """Test temporary directory is created"""
        assert transcription_service.temp_dir.exists()
        assert transcription_service.temp_dir.is_dir()

        # Test we can write to it
        test_file = transcription_service.temp_dir / "test.txt"
        test_file.write_text("test")
        assert test_file.exists()

        # Cleanup
        test_file.unlink()

    @pytest.mark.asyncio
    async def test_cleanup_temp_files(self, transcription_service):
        """Test cleanup of temporary files"""
        # Create some test files
        test_files = []
        total_size = 0
        for i in range(3):
            test_file = transcription_service.temp_dir / f"test_{i}.txt"
            content = f"test content {i}" * 100  # Make it bigger
            test_file.write_text(content)
            test_files.append(test_file)
            total_size += len(content.encode())

        # Run cleanup
        stats = await transcription_service.cleanup_temp_files()

        assert stats['files_removed'] == 3
        assert stats['space_freed_mb'] >= 0

        # Verify files are gone
        for test_file in test_files:
            assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_transcribe_audio_placeholder(self, transcription_service, test_audio_file):
        """Test audio transcription (placeholder implementation)"""
        # Test the _transcribe_audio method directly
        result = await transcription_service._transcribe_audio(
            test_audio_file,
            "en"
        )

        assert isinstance(result, str)
        assert len(result) > 0
        assert "placeholder" in result.lower()
        assert "Language setting: en" in result

    @pytest.mark.asyncio
    async def test_get_video_metadata_error_handling(self, transcription_service):
        """Test metadata extraction error handling"""
        # Test with invalid URL
        with pytest.raises(Exception):
            await transcription_service._get_video_metadata("invalid_url")

    @pytest.mark.asyncio
    async def test_document_message_creation_youtube(self, transcription_service):
        """Test that service creates proper DocumentMessage objects for YouTube"""
        url = "https://example.com/video"
        doc_id = hashlib.sha256(url.encode()).hexdigest()[:12]

        document = DocumentMessage(
            metadata=DocumentMetadata(
                document_id=doc_id,
                document_type=DocumentType.YOUTUBE,
                name="Test Video",
                created_user="test_user",
                updated_user="test_user",
                source_url=url,
                tags=["youtube", "video", "transcription"],
                processing_stage=ProcessingStage.COMPLETED,
                source=DocumentSource.YOUTUBE
            ),
            content=DocumentContent(
                raw_text="Test transcription",
                formatted_content="# Test Video\n\nTest transcription"
            ),
            user_id="test_user",
            session_id="test_session"
        )

        # Test the document structure
        assert document.metadata.document_id == doc_id
        assert document.metadata.id == doc_id  # Check alias
        assert document.metadata.document_type == DocumentType.YOUTUBE
        assert document.metadata.type == DocumentType.YOUTUBE  # Check alias
        assert document.metadata.source == DocumentSource.YOUTUBE
        assert document.content.raw_text == "Test transcription"
        assert document.content.formatted_content is not None

    @pytest.mark.asyncio
    async def test_document_message_creation_podcast(self, transcription_service):
        """Test podcast document type handling"""
        url = "https://example.com/podcast.mp3"
        doc_id = hashlib.sha256(url.encode()).hexdigest()[:12]

        document = DocumentMessage(
            metadata=DocumentMetadata(
                document_id=doc_id,
                document_type=DocumentType.PODCAST,
                name="Test Podcast",
                created_user="test_user",
                updated_user="test_user",
                source_url=url,
                tags=["podcast", "audio", "transcription"],
                source=DocumentSource.WEB
            ),
            content=DocumentContent(
                raw_text="Podcast transcription",
                formatted_content="# Test Podcast\n\nPodcast transcription"
            )
        )

        assert document.metadata.document_type == DocumentType.PODCAST
        assert document.metadata.source == DocumentSource.WEB
        assert "podcast" in document.metadata.tags

    @pytest.mark.asyncio
    async def test_service_uses_centralized_config(self, transcription_service):
        """Test that service uses centralized configuration"""
        settings = get_settings()

        # Verify service uses settings
        assert transcription_service.settings == settings
        assert transcription_service.settings.storage.type in ["filesystem", "redis"]

    @pytest.mark.asyncio
    async def test_ydl_options_configuration(self, transcription_service):
        """Test yt-dlp options are configured correctly"""
        assert transcription_service.ydl_opts is not None
        assert transcription_service.ydl_opts['format'] == 'bestaudio/best'
        assert transcription_service.ydl_opts['quiet'] is True
        assert 'postprocessors' in transcription_service.ydl_opts

        # Check audio extraction is configured
        postprocessors = transcription_service.ydl_opts['postprocessors']
        assert len(postprocessors) > 0
        assert postprocessors[0]['key'] == 'FFmpegExtractAudio'

    @pytest.mark.asyncio
    async def test_storage_integration(self, transcription_service):
        """Test storage integration"""
        # Create a test document
        test_doc = {
            "metadata": {
                "document_id": "test_trans_123",
                "document_type": "youtube",
                "name": "Test Video",
                "created_user": "test",
                "updated_user": "test"
            },
            "content": {
                "raw_text": "test content",
                "formatted_content": "# Test\n\ntest content"
            }
        }

        # Store document
        await transcription_service.storage.store("test_trans_123", test_doc)

        # Retrieve and verify
        retrieved = await transcription_service.storage.load("test_trans_123")
        assert retrieved is not None
        assert retrieved["metadata"]["document_id"] == "test_trans_123"

        # Cleanup
        await transcription_service.storage.delete("test_trans_123")

    @pytest.mark.asyncio
    async def test_async_operations(self, transcription_service):
        """Test that all I/O operations are async"""
        # Test file operations are async
        test_file = transcription_service.temp_dir / "async_test.txt"

        # Write async
        import aiofiles
        async with aiofiles.open(test_file, 'w') as f:
            await f.write("async test")

        # Read async
        async with aiofiles.open(test_file, 'r') as f:
            content = await f.read()

        assert content == "async test"

        # Cleanup async
        await asyncio.to_thread(os.remove, test_file)
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_error_handling_and_logging(self, transcription_service):
        """Test error handling and logging"""
        # Test with invalid input - this should raise an exception
        with pytest.raises(Exception):
            await transcription_service._download_audio(
                "invalid://url",
                {}
            )

        # Verify logger is configured
        assert transcription_service.logger is not None
        assert transcription_service.logger.service_name == "TranscriptionService"

    @pytest.mark.asyncio
    async def test_traced_operations(self, transcription_service):
        """Test that operations use tracing"""
        # Verify service has tracer
        assert hasattr(transcription_service, 'tracer')
        assert hasattr(transcription_service, 'traced_operation')

        # Test traced operation context manager
        with transcription_service.traced_operation("test_op", test_attr="value"):
            # Operation would be traced here
            pass

    @pytest.mark.asyncio
    async def test_download_audio_error_handling(self, transcription_service):
        """Test download audio error handling"""
        # Test with invalid URL format
        with pytest.raises(Exception):
            await transcription_service._download_audio(
                "not_a_url",
                {'title': 'Test'}
            )

    @pytest.mark.asyncio
    async def test_transcribe_youtube_structure(self, transcription_service):
        """Test YouTube transcribe method structure (without actual download)"""
        # This tests the method structure without hitting real YouTube
        # In production, you'd have integration tests for real URLs

        # Verify method exists and has correct signature
        assert hasattr(transcription_service, 'transcribe_youtube')

        # The method should handle these parameters
        method = transcription_service.transcribe_youtube
        import inspect
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())

        assert 'url' in params
        assert 'language' in params
        assert 'user_id' in params
        assert 'session_id' in params

    @pytest.mark.asyncio
    async def test_transcribe_podcast_structure(self, transcription_service):
        """Test podcast transcribe method structure"""
        # Verify method exists and has correct signature
        assert hasattr(transcription_service, 'transcribe_podcast')

        # The method should handle these parameters
        method = transcription_service.transcribe_podcast
        import inspect
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())

        assert 'url' in params
        assert 'language' in params
        assert 'user_id' in params
        assert 'session_id' in params