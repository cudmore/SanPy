"""Open remote NWB files through an fsspec-backed local cache."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, Protocol

import fsspec
import h5py
import lindi
from fsspec.implementations.cached import CachingFileSystem
from platformdirs import user_cache_dir

from sanpy.sanpyLogger import get_logger

logger = get_logger(__name__)


class NwbTransport(Protocol):
    """Define the remote HDF5 operation required by the DANDI backend."""

    cache_dir: Path

    def open_h5(self, content_url: str) -> Iterator[h5py.File]:
        """Open a remote NWB resource as an HDF5-compatible file.

        Args:
            content_url: HTTP URL for an immutable DANDI asset.

        Returns:
            Context manager yielding an HDF5-compatible file.
        """
        ...


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

    @contextmanager
    def open_h5(self, content_url: str) -> Iterator[h5py.File]:
        """Open a remote NWB resource through h5py.

        Args:
            content_url: HTTP URL for an immutable DANDI asset.

        Yields:
            Open h5py file backed by the fsspec stream.
        """
        with self.open(content_url) as remote_file:
            with h5py.File(remote_file, mode="r") as h5_file:
                yield h5_file


class LindiNwbTransport:
    """Open remote NWB files through LINDI's persistent chunk cache.

    Attributes:
        cache_dir: Directory used for persistent LINDI cache data.
    """

    def __init__(
        self,
        cache_dir: Path | str | None = None,
        use_cache: bool = True,
    ) -> None:
        """Initialize the LINDI transport.

        Args:
            cache_dir: Optional cache-directory override. The platform-specific
                SanPy LINDI cache directory is used when omitted.
            use_cache: Whether remote chunks should persist across processes.
        """
        default_cache = (
            Path(user_cache_dir("SanPy", appauthor=False)) / "dandi" / "lindi"
        )
        self.cache_dir = Path(cache_dir) if cache_dir is not None else default_cache
        self._use_cache = use_cache

    @contextmanager
    def open_h5(self, content_url: str) -> Iterator[h5py.File]:
        """Open a remote NWB resource as an HDF5-compatible LINDI file.

        Args:
            content_url: HTTP URL for an immutable DANDI asset.

        Yields:
            Open LINDI file accepted by PyNWB.
        """
        local_cache: lindi.LocalCache | None = None
        if self._use_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            local_cache = lindi.LocalCache(cache_dir=str(self.cache_dir))
        logger.info("Opening remote NWB asset through LINDI:")
        logger.info(f"  {content_url}")
        h5_file = lindi.LindiH5pyFile.from_hdf5_file(
            content_url,
            local_cache=local_cache,
        )
        try:
            yield h5_file
        finally:
            if getattr(h5_file, "_is_open", False):
                h5_file.close()
