from abc import ABC, abstractmethod
import re
import shutil
from pathlib import Path
from typing import Optional

from app.core.config import get_settings

SAFE_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]{1,128}$")


class StorageBackend(ABC):
    @abstractmethod
    def save_video(self, source_path: Path, storage_key: str) -> str:
        """Persist a generated video and return its storage key."""

    @abstractmethod
    def get_local_path(self, storage_key: str) -> Optional[Path]:
        """Return a local filesystem path if supported and file exists."""

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Check whether the stored object exists."""


class LocalStorageBackend(StorageBackend):
    """Stores generated MP4 files on the local filesystem.

    Note: Render free-tier filesystems are ephemeral across deploys/restarts.
    For persistent production storage, implement an S3/Cloudflare R2 adapter
    behind StorageBackend.
    """

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir.resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _safe_resolve(self, storage_key: str) -> Path:
        filename = Path(storage_key).name
        if filename != storage_key or not SAFE_KEY_PATTERN.match(filename):
            raise ValueError("Invalid storage key.")
        resolved = (self.base_dir / filename).resolve()
        if resolved.parent != self.base_dir:
            raise ValueError("Path traversal detected in storage key.")
        return resolved

    def save_video(self, source_path: Path, storage_key: str) -> str:
        target = self._safe_resolve(storage_key)
        shutil.copy2(source_path, target)
        return storage_key

    def get_local_path(self, storage_key: str) -> Optional[Path]:
        try:
            target = self._safe_resolve(storage_key)
        except ValueError:
            return None
        if target.exists() and target.is_file():
            return target
        return None

    def exists(self, storage_key: str) -> bool:
        return self.get_local_path(storage_key) is not None


def get_storage_service() -> StorageBackend:
    settings = get_settings()
    backend = settings.STORAGE_BACKEND.strip().lower()
    if backend == "local":
        return LocalStorageBackend(settings.storage_dir)
    raise ValueError(
        f"Unsupported STORAGE_BACKEND '{settings.STORAGE_BACKEND}'. Currently supported: local."
    )
