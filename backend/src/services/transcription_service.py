"""Transcription service for YouTube videos and podcasts

This service handles:
- YouTube video download and transcription
- Podcast download and transcription
- Audio extraction from video files
- Transcription using various methods
"""

import os
import asyncio
import tempfile
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
import hashlib
from datetime import datetime

import aiofiles
import yt_dlp
# from pydub import AudioSegment  # Disabled: audioop removed in Python 3.13

from .base_service import BaseService
from ..models.document import (
    DocumentMessage,
    DocumentMetadata,
    DocumentContent,
    DocumentType,
    ContentBlock,
    ProcessingStage,
    DocumentSource
)
from ..core.config import get_settings
from ..core.logger import CentralizedLogger
from ..storage.storage_factory import StorageFactory, StorageType


class TranscriptionService(BaseService):
    """Service for transcribing YouTube videos and podcasts"""

    def __init__(self):
        """Initialize transcription service"""
        super().__init__("TranscriptionService")
        self.settings = get_settings()
        self.logger = CentralizedLogger("TranscriptionService")

        # Configure storage
        self.storage = StorageFactory.create(
            StorageType(self.settings.storage.type)
        )

        # Configure paths from settings
        self.temp_dir = Path(tempfile.gettempdir()) / "mavn_transcription"
        self.temp_dir.mkdir(exist_ok=True)

        # Configure yt-dlp options
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'outtmpl': str(self.temp_dir / '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        # Add cookie support from settings if configured
        if hasattr(self.settings, 'transcription'):
            if hasattr(self.settings.transcription, 'youtube_cookies_browser'):
                self.ydl_opts['cookiesfrombrowser'] = (
                    self.settings.transcription.youtube_cookies_browser,
                )
            elif hasattr(self.settings.transcription, 'youtube_cookies_file'):
                self.ydl_opts['cookiefile'] = (
                    self.settings.transcription.youtube_cookies_file
                )

    async def health_check(self) -> Dict[str, Any]:
        """Check service health

        Returns:
            Health status dictionary
        """
        with self.traced_operation("health_check"):
            try:
                # Check temp directory is writable
                test_file = self.temp_dir / "health_check.txt"
                async with aiofiles.open(test_file, 'w') as f:
                    await f.write("health check")

                # Clean up test file
                await asyncio.to_thread(os.remove, test_file)

                # Check yt-dlp availability
                import yt_dlp.version
                version = yt_dlp.version.__version__

                return {
                    "service": "TranscriptionService",
                    "status": "healthy",
                    "temp_dir": str(self.temp_dir),
                    "yt_dlp_version": version,
                    "storage_type": self.settings.storage.type
                }
            except Exception as e:
                self.logger.error(f"Health check failed: {str(e)}")
                return {
                    "service": "TranscriptionService",
                    "status": "unhealthy",
                    "error": str(e)
                }

    async def transcribe_youtube(
        self,
        url: str,
        language: Optional[str] = None,
        user_id: str = "anonymous",
        session_id: Optional[str] = None
    ) -> DocumentMessage:
        """Transcribe a YouTube video

        Args:
            url: YouTube video URL
            language: Target language for transcription
            user_id: User identifier
            session_id: Session identifier

        Returns:
            DocumentMessage with transcription
        """
        with self.traced_operation(
            "transcribe_youtube",
            url=url,
            language=language,
            user_id=user_id,
            session_id=session_id
        ):
            try:
                # Download video metadata first
                metadata = await self._get_video_metadata(url)

                # Create document message
                doc_id = hashlib.sha256(url.encode()).hexdigest()[:12]
                document = DocumentMessage(
                    metadata=DocumentMetadata(
                        document_id=doc_id,
                        document_type=DocumentType.YOUTUBE,
                        name=metadata.get('title', 'Untitled'),
                        created_user=user_id,
                        updated_user=user_id,
                        source_url=url,
                        tags=["youtube", "video", "transcription"]
                    ),
                    content=DocumentContent(
                        raw_text="",
                        formatted_content=""
                    ),
                    user_id=user_id,
                    session_id=session_id
                )

                # Download and extract audio
                audio_path = await self._download_audio(url, metadata)

                try:
                    # Transcribe audio
                    transcription = await self._transcribe_audio(
                        audio_path,
                        language or "auto"
                    )

                    # Update document with transcription
                    document.content.raw_text = transcription
                    document.content.formatted_content = f"# {metadata.get('title', 'Untitled')}\n\n{transcription}\n\n---\n\n**Duration**: {metadata.get('duration')} seconds\n**Channel**: {metadata.get('channel')}\n**Upload Date**: {metadata.get('upload_date')}"

                    # Update metadata
                    document.metadata.updated_timestamp = datetime.utcnow()
                    document.metadata.summary = transcription[:200] + "..." if len(transcription) > 200 else transcription

                    # Store document
                    await self.storage.store(doc_id, document.model_dump())

                    self.logger.info(f"Successfully transcribed YouTube video: {url}")
                    return document

                finally:
                    # Clean up audio file
                    if await asyncio.to_thread(os.path.exists, audio_path):
                        await asyncio.to_thread(os.remove, audio_path)

            except Exception as e:
                self.logger.error(f"Failed to transcribe YouTube video {url}: {str(e)}")
                raise

    async def transcribe_podcast(
        self,
        url: str,
        language: Optional[str] = None,
        user_id: str = "anonymous",
        session_id: Optional[str] = None
    ) -> DocumentMessage:
        """Transcribe a podcast

        Args:
            url: Podcast URL
            language: Target language for transcription
            user_id: User identifier
            session_id: Session identifier

        Returns:
            DocumentMessage with transcription
        """
        with self.traced_operation(
            "transcribe_podcast",
            url=url,
            language=language,
            user_id=user_id,
            session_id=session_id
        ):
            try:
                # For podcasts, we use the same yt-dlp approach
                # It supports many podcast platforms
                metadata = await self._get_video_metadata(url)

                # Create document message
                doc_id = hashlib.sha256(url.encode()).hexdigest()[:12]
                document = DocumentMessage(
                    metadata=DocumentMetadata(
                        document_id=doc_id,
                        document_type=DocumentType.PODCAST,
                        name=metadata.get('title', 'Untitled Podcast'),
                        created_user=user_id,
                        updated_user=user_id,
                        source_url=url,
                        tags=["podcast", "audio", "transcription"]
                    ),
                    content=DocumentContent(
                        raw_text="",
                        formatted_content=""
                    ),
                    user_id=user_id,
                    session_id=session_id
                )

                # Download audio
                audio_path = await self._download_audio(url, metadata)

                try:
                    # Transcribe audio
                    transcription = await self._transcribe_audio(
                        audio_path,
                        language or "auto"
                    )

                    # Update document with transcription
                    document.content.raw_text = transcription
                    document.content.formatted_content = f"# {metadata.get('title', 'Untitled Podcast')}\n\n{transcription}\n\n---\n\n**Duration**: {metadata.get('duration')} seconds\n**Episode**: {metadata.get('episode')}\n**Series**: {metadata.get('series')}"

                    # Update metadata
                    document.metadata.updated_timestamp = datetime.utcnow()
                    document.metadata.summary = transcription[:200] + "..." if len(transcription) > 200 else transcription

                    # Store document
                    await self.storage.store(doc_id, document.model_dump())

                    self.logger.info(f"Successfully transcribed podcast: {url}")
                    return document

                finally:
                    # Clean up audio file
                    if await asyncio.to_thread(os.path.exists, audio_path):
                        await asyncio.to_thread(os.remove, audio_path)

            except Exception as e:
                self.logger.error(f"Failed to transcribe podcast {url}: {str(e)}")
                raise

    async def _get_video_metadata(self, url: str) -> Dict[str, Any]:
        """Get video/audio metadata using yt-dlp

        Args:
            url: Video/audio URL

        Returns:
            Metadata dictionary
        """
        with self.traced_operation("get_video_metadata", url=url):
            try:
                # Run yt-dlp in thread pool to avoid blocking
                def extract_info():
                    with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                        return ydl.extract_info(url, download=False)

                info = await asyncio.to_thread(extract_info)

                return {
                    'title': info.get('title'),
                    'duration': info.get('duration'),
                    'channel': info.get('channel') or info.get('uploader'),
                    'upload_date': info.get('upload_date'),
                    'description': info.get('description'),
                    'thumbnail': info.get('thumbnail'),
                    'episode': info.get('episode'),
                    'series': info.get('series')
                }
            except Exception as e:
                self.logger.error(f"Failed to get metadata for {url}: {str(e)}")
                raise

    async def _download_audio(self, url: str, metadata: Dict[str, Any]) -> str:
        """Download audio from URL

        Args:
            url: Video/audio URL
            metadata: Video metadata

        Returns:
            Path to downloaded audio file
        """
        with self.traced_operation("download_audio", url=url):
            try:
                # Create unique filename
                file_hash = hashlib.sha256(url.encode()).hexdigest()[:8]
                audio_file = self.temp_dir / f"{file_hash}.mp3"

                # Configure download options
                download_opts = self.ydl_opts.copy()
                download_opts['outtmpl'] = str(audio_file.with_suffix('.%(ext)s'))

                # Download in thread pool
                def download():
                    with yt_dlp.YoutubeDL(download_opts) as ydl:
                        ydl.download([url])

                await asyncio.to_thread(download)

                # Find the actual downloaded file (might have different extension)
                for ext in ['.mp3', '.m4a', '.wav', '.opus']:
                    check_file = audio_file.with_suffix(ext)
                    if await asyncio.to_thread(os.path.exists, check_file):
                        return str(check_file)

                # If original file exists, return it
                if await asyncio.to_thread(os.path.exists, audio_file):
                    return str(audio_file)

                raise FileNotFoundError(f"Downloaded audio file not found: {audio_file}")

            except Exception as e:
                self.logger.error(f"Failed to download audio from {url}: {str(e)}")
                raise

    async def _transcribe_audio(self, audio_path: str, language: str) -> str:
        """Transcribe audio file

        This is a placeholder that would integrate with actual transcription services
        like OpenAI Whisper, Google Speech-to-Text, or AWS Transcribe

        Args:
            audio_path: Path to audio file
            language: Target language

        Returns:
            Transcribed text
        """
        with self.traced_operation(
            "transcribe_audio",
            audio_path=audio_path,
            language=language
        ):
            try:
                # For now, return a placeholder
                # In production, this would call actual transcription API

                # Get audio duration for context
                # Note: pydub disabled due to Python 3.13 compatibility
                # In production, use ffprobe or other methods
                duration_seconds = 60.0  # Placeholder duration

                # Placeholder transcription
                # In real implementation, this would:
                # 1. Split audio into chunks if needed
                # 2. Send to transcription service (Whisper, etc.)
                # 3. Combine results

                transcription = (
                    f"[Transcription placeholder for {duration_seconds:.1f} seconds of audio]\n\n"
                    f"This is where the actual transcription would appear. "
                    f"In a production environment, this would integrate with:\n"
                    f"- OpenAI Whisper API\n"
                    f"- Google Speech-to-Text\n"
                    f"- AWS Transcribe\n"
                    f"- Or a local Whisper model\n\n"
                    f"Language setting: {language}"
                )

                self.logger.info(
                    f"Transcribed {duration_seconds:.1f} seconds of audio "
                    f"(placeholder implementation)"
                )

                return transcription

            except Exception as e:
                self.logger.error(f"Failed to transcribe audio {audio_path}: {str(e)}")
                raise

    async def cleanup_temp_files(self) -> Dict[str, Any]:
        """Clean up temporary files

        Returns:
            Cleanup statistics
        """
        with self.traced_operation("cleanup_temp_files"):
            try:
                files_removed = 0
                space_freed = 0

                # List all files in temp directory
                for file_path in self.temp_dir.iterdir():
                    if file_path.is_file():
                        # Get file size before deletion
                        size = await asyncio.to_thread(os.path.getsize, file_path)
                        space_freed += size

                        # Remove file
                        await asyncio.to_thread(os.remove, file_path)
                        files_removed += 1

                self.logger.info(
                    f"Cleaned up {files_removed} files, "
                    f"freed {space_freed / 1024 / 1024:.2f} MB"
                )

                return {
                    "files_removed": files_removed,
                    "space_freed_mb": space_freed / 1024 / 1024
                }

            except Exception as e:
                self.logger.error(f"Failed to cleanup temp files: {str(e)}")
                raise


# Register with factory
from .service_factory import ServiceFactory, ServiceType
ServiceFactory.register(ServiceType.TRANSCRIPTION, TranscriptionService)