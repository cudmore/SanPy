"""Tests for standalone remote NWB transport configuration."""

from pathlib import Path

from dandi_transport import FsspecNwbTransport, LindiNwbTransport


def test_uses_cache_override(tmp_path: Path) -> None:
    """Retain an explicitly supplied cache directory.

    Args:
        tmp_path: Temporary test directory.
    """
    cache_dir = tmp_path / "dandi-cache"

    transport = FsspecNwbTransport(cache_dir=cache_dir)

    assert transport.cache_dir == cache_dir
    assert not cache_dir.exists()


def test_lindi_uses_cache_override(tmp_path: Path) -> None:
    """Retain a LINDI cache override without eagerly creating it.

    Args:
        tmp_path: Temporary test directory.
    """
    cache_dir = tmp_path / "lindi-cache"

    transport = LindiNwbTransport(cache_dir=cache_dir)

    assert transport.cache_dir == cache_dir
    assert not cache_dir.exists()
