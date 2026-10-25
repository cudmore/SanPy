"""Resolve and stream published DANDI NWB assets into SanPy."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, ContextManager, Protocol

import h5py
from pynwb import NWBHDF5IO

from sanpy.fileloaders.fileLoader_nwb import fileLoader_nwb


class NwbTransport(Protocol):
    """Define the one remote HDF5 operation required by the NWB decoder."""

    def open_h5(self, content_url: str) -> ContextManager[h5py.File]:
        """Open an HDF5-compatible remote NWB handle.

        Args:
            content_url: Direct URL for an immutable published asset.

        Returns:
            Context manager yielding an HDF5-compatible file.
        """
        ...


@dataclass(frozen=True)
class RemoteNwbAsset:
    """Identify one published NWB asset.

    Attributes:
        dandiset_id: Six-digit DANDI identifier.
        version: Immutable published version.
        asset_id: Immutable asset identifier.
        path: Asset path relative to the Dandiset root.
        content_url: Direct content URL resolved by the DANDI API.
    """

    dandiset_id: str
    version: str
    asset_id: str
    path: str
    content_url: str


@dataclass(frozen=True)
class RemoteDandiset:
    """Represent one published Dandiset's NWB assets.

    Attributes:
        dandiset_id: Six-digit DANDI identifier.
        version: Immutable published version.
        assets: NWB assets sorted by relative path.
    """

    dandiset_id: str
    version: str
    assets: tuple[RemoteNwbAsset, ...]


def open_remote_dandiset(resource: str) -> RemoteDandiset:
    """Resolve all NWB assets in an explicit published DANDI version.

    Args:
        resource: DANDI URL or identifier accepted by ``dandi``.

    Returns:
        Immutable published Dandiset asset catalog.

    Raises:
        ImportError: If the optional DANDI dependency is unavailable.
        ValueError: If the resource is not an explicit published Dandiset.
        RuntimeError: If DANDI API access fails.
    """
    try:
        from dandi.dandiarchive import DandisetURL, parse_dandi_url
    except ImportError as error:
        raise ImportError(
            "Remote DANDI access requires the SanPy 'dandi' extra"
        ) from error

    try:
        parsed = parse_dandi_url(resource)
    except Exception as error:
        raise ValueError(f"Could not parse DANDI resource {resource!r}: {error}") from error
    if not isinstance(parsed, DandisetURL):
        raise ValueError("DANDI resource must identify a whole Dandiset")
    version = parsed.version_id
    if version is None or str(version).lower() == "draft":
        raise ValueError("An explicit published Dandiset version is required")

    try:
        with parsed.navigate(strict=True) as (_client, _dandiset, remote_assets):
            assets = tuple(
                RemoteNwbAsset(
                    dandiset_id=str(parsed.dandiset_id),
                    version=str(version),
                    asset_id=str(asset.identifier),
                    path=str(asset.path),
                    content_url=str(
                        asset.get_content_url(follow_redirects=1, strip_query=True)
                    ),
                )
                for asset in remote_assets
                if str(asset.path).lower().endswith(".nwb")
            )
    except Exception as error:
        raise RuntimeError(f"Could not list published DANDI assets: {error}") from error
    return RemoteDandiset(
        dandiset_id=str(parsed.dandiset_id),
        version=str(version),
        assets=tuple(sorted(assets, key=lambda asset: asset.path)),
    )


def read_remote_recording(
    asset: RemoteNwbAsset,
    transport: NwbTransport | None = None,
) -> Any:
    """Stream one published NWB asset through the shared SanPy decoder.

    Args:
        asset: Published NWB asset to load.
        transport: Optional transport override for focused tests or custom I/O.

    Returns:
        Fully materialized SanPy ``bAnalysis`` independent of the remote handle.

    Raises:
        ImportError: If the default LINDI dependency is unavailable.
        ValueError: If SanPy cannot represent the NWB recording.
    """
    active_transport = transport or _LindiTransport()
    with active_transport.open_h5(asset.content_url) as h5_file:
        with NWBHDF5IO(file=h5_file, load_namespaces=True) as io:
            loader = fileLoader_nwb.from_nwbfile(
                io.read(), source_identity=asset.path, load_data=True
            )
            if loader.getLoadError():
                raise ValueError(f"SanPy could not load remote NWB asset: {asset.path}")
            import sanpy

            return sanpy.bAnalysis.from_file_loader(loader)


class _LindiTransport:
    """Open remote HDF5 content through LINDI's range reader."""

    @contextmanager
    def open_h5(self, content_url: str) -> Iterator[h5py.File]:
        """Open one remote NWB URL with LINDI.

        Args:
            content_url: Direct published asset URL.

        Yields:
            LINDI HDF5-compatible file.

        Raises:
            ImportError: If LINDI is not installed.
        """
        try:
            import lindi
        except ImportError as error:
            raise ImportError(
                "Remote DANDI streaming requires the SanPy 'dandi' extra"
            ) from error
        h5_file = lindi.LindiH5pyFile.from_hdf5_file(content_url)
        try:
            yield h5_file
        finally:
            h5_file.close()
