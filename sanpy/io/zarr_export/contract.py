"""Constants for the SanPy Zarr collection format."""

FORMAT_NAME = "sanpy-zarr"
FORMAT_VERSION = "1.0-draft"
ZARR_FORMAT = 3
TABLE_FORMATS = frozenset({"csv", "parquet", "both"})
DEFAULT_CHUNK_POINTS = 65_536
