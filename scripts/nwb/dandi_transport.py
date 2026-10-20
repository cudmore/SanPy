"""Open remote NWB files through an fsspec-backed local cache."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

import fsspec
from fsspec.implementations.cached import CachingFileSystem
from platformdirs import user_cache_dir

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


class FsspecNwbTransport:
    """Open seekable HTTP resources using an fsspec block cache.

    Attributes:
        cache_dir: Directory used for persistent fsspec cache files.
    """

    def __init__(
        self,
        cache_dir: Path | str | None = None,
        use_cache: bool = True,
    ) -> None:
        """Initialize the HTTP transport.

        Args:
            cache_dir: Optional cache-directory override. The platform-specific
                SanPy cache directory is used when omitted.
            use_cache: Whether remote byte ranges should persist on disk.
        """
        default_cache = Path(user_cache_dir("SanPy", appauthor=False)) / "dandi"
        self.cache_dir = Path(cache_dir) if cache_dir is not None else default_cache
        self._use_cache = use_cache

    @contextmanager
    def open(self, content_url: str) -> Iterator[BinaryIO]:
        """Open a seekable remote binary stream.

        Args:
            content_url: HTTP URL for an immutable DANDI asset.

        Yields:
            Seekable binary stream suitable for ``h5py.File``.

        Raises:
            OSError: If the cache directory or remote resource cannot be opened.
        """
        http_filesystem = fsspec.filesystem("http")
        filesystem: object
        if self._use_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            filesystem = CachingFileSystem(
                fs=http_filesystem,
                cache_storage=str(self.cache_dir),
                check_files=False,
            )
        else:
            filesystem = http_filesystem

        logger.info(f'Opening remote NWB asset:')
        logger.info(f'  {content_url}')

        with filesystem.open(content_url, "rb") as remote_file:  # type: ignore[attr-defined]
            yield remote_file

