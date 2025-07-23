"""
TifFileBackend - Backend class for managing .tif file data and metadata.

TWO-PHASE SYSTEM:
================
This backend uses a two-phase approach to separate fast file discovery from expensive computations:

1. PHASE 1: File Discovery (_scan_files)
   - Fast scanning of directory structure
   - Basic metadata extraction (paths, folders)
   - No expensive computations

2. PHASE 2: Analysis (_analyze_files)
   - Expensive computations (TifInfo parsing, etc.)
   - Runs only once per file (tracked by _analyzed column)
   - Results cached in DataFrame columns

HOW TO ADD NEW COLUMNS:
======================

1. ADD TO COLUMN_CONFIG DICTIONARY (around line 140):
   Add your column with its configuration including data type:
   'your_column': ColumnConfig(
       display_name='Your Column',  # What users see
       column_type=str,             # Data type: str, int, bool, float, object, etc.
       width=100,                   # Column width (None for auto)
       stretch=False,               # Should column stretch?
       editable=False,              # Can users edit this column?
       widget_type=None,            # 'checkbox', 'dropdown', etc.
       tree_visible=True,           # Show in tree widget?
       table_visible=True,          # Show in table widget?
       sortable=True                # Can users sort by this column?
   )

2. ADD DATA POPULATION:
   For basic metadata (fast): Add to _scan_files() method
   For expensive computations: Add to _analyze_files() method

3. ADD TYPE CONVERSION (if needed, around line 280):
   If your column needs special type conversion when loading from CSV:
   if 'your_column' in common_cols:
       update_df['your_column'] = your_conversion_function(update_df['your_column'])

4. ADD TYPE CONVERSION IN MAIN LOOP (if needed, around line 300):
   In the column update loop, add your type conversion:
   elif col == 'your_column':
       updated_column = your_conversion_function(updated_column)

EXAMPLES:
- String column: Just add to COLUMN_CONFIG with column_type=str
- Integer column: Add column_type=int and type conversion in _load_saved_state
- Boolean column: Add column_type=bool and to checkbox conversion list
- Expensive computed column: Add calculation in _analyze_files() method

SPECIAL COLUMNS:
- _KymRoiAnalysis: Special column that stores KymRoiAnalysis objects in memory during runtime.
  This column is NOT saved to CSV files and is used for lazy loading of analysis objects.
  Use get_kym_roi_analysis(row_index) or get_kym_roi_analysis_by_path(tif_path) to access.
- _analyzed: Tracks whether expensive analysis has been run on each file.
  Used internally to ensure each file is analyzed only once.

WIDGET COMPATIBILITY:
- Table widget: Automatically shows columns with table_visible=True
- Tree widget: Currently uses hardcoded columns (needs refactoring)

API METHODS:
- force_reanalyze_all(): Re-run expensive computations on all files
- analyze_unanalyzed_files(): Run expensive computations only on unanalyzed files
- get_analysis_status(): Get counts of analyzed/unanalyzed files
"""

import os
import re
from pathlib import Path

# import random  # Uncomment when adding columns that need random data
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
import pandas as pd

from sanpy.sanpyLogger import get_logger

from sanpy.kym.tif_info import TifInfo
# from sanpy.kym.tif_pool import TiffPool  # circular import

from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis

logger = get_logger(__name__)


@dataclass
class ColumnConfig:
    """Configuration for a column in the TifFileBackend.
    
    This dataclass provides a type-safe way to configure column behavior
    and appearance across different UI widgets.
    """

    display_name: str
    column_type: type = str  # Default to string type
    width: Optional[int] = 100  # Default width for all columns
    editable: bool = False
    widget_type: Optional[str] = None
    backend_field: Optional[str] = None
    tree_visible: bool = False
    table_visible: bool = False
    sortable: bool = True
    default_value: Any = None  # Default value for the column
    tooltip: Optional[str] = None  # Tooltip text for the column header
    
    def __post_init__(self):
        """Auto-set backend_field if not provided."""
        if self.backend_field is None:
            # Convert display_name to snake_case for backend field
            self.backend_field = self.display_name.lower().replace(' ', '_')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return {
            'display_name': self.display_name,
            'column_type': self.column_type,
            'width': self.width,
            'editable': self.editable,
            'widget_type': self.widget_type,
            'backend_field': self.backend_field,
            'tree_visible': self.tree_visible,
            'table_visible': self.table_visible,
            'sortable': self.sortable,
            'default_value': self.default_value,
            'tooltip': self.tooltip,
        }


class TifFileBackend:
    """Backend class for managing .tif file data and metadata with advanced analysis capabilities.
    
    This class provides a comprehensive solution for scanning, analyzing, and managing .tif files
    in a directory structure. It uses a two-phase approach to separate fast file discovery from
    expensive computations, making it efficient for large datasets.
    
    **Key Features:**
    
    - **Two-phase system**: Fast file discovery + expensive analysis
    - **Automatic metadata extraction**: From filenames and TIF headers
    - **Acquisition parameter extraction**: From KymRoiAnalysis objects
    - **State persistence**: Save/load analysis results to CSV
    - **Incremental updates**: Only re-analyze new or changed files
    - **Flexible filtering**: By condition, region, repeat, etc.
    - **Memory-efficient**: Lazy loading of KymRoiAnalysis objects
    
    **Typical Usage:**
    
    ```python
    from sanpy.kym.tif_file_backend import TifFileBackend
    
    # Create backend for a directory
    backend = TifFileBackend(
        root_path="/path/to/tif/files",
        exclude_folders=["sanpy-reports-pdf"],
        sort_by_grandparent=True
    )
    
    # Get analyzed files
    files = backend.get('files')
    
    # Force re-analysis if needed
    backend.force_reanalyze_all()
    
    # Save state
    backend.save_state()
    ```
    
    **Column System:**
    
    The backend uses a configurable column system defined in `COLUMN_CONFIG`. Each column
    has properties like display name, data type, width, visibility, and editability.
    
    **Analysis Status:**
    
    - `_analyzed`: Tracks whether expensive analysis has been performed
    - Use `get_analysis_status()` to check progress
    - Use `analyze_unanalyzed_files()` to continue analysis
    
    **File Organization:**
    
    Files are organized by folder hierarchy:
    - `great_grandparent_folder`: Top-level experiment folder
    - `grandparent_folder`: Condition folder (e.g., "Control", "Treatment")
    - `parent_folder`: Sub-folder within condition
    - `filename`: The actual .tif file
    
    Attributes
    ----------
    root_path : str
        Root directory containing .tif files
    exclude_folders : List[str]
        Folder names to exclude from scanning
    sort_by_grandparent : bool
        Whether to sort by grandparent folder (True) or parent folder (False)
    max_depth : int
        Maximum depth of folders to scan
    df : pd.DataFrame
        Main data storage with all file metadata and analysis results
    COLUMN_CONFIG : Dict[str, ColumnConfig]
        Configuration for all available columns
        
    See Also
    --------
    ColumnConfig : Configuration class for individual columns
    KymRoiAnalysis : Analysis class for individual TIF files
    TifInfo : Filename parsing utility
    """

    # Define column structure for easy modification
    # IMPORTANT: When adding new columns, you need to:
    # 1. Add the column here with its configuration including data type
    # 2. Add data population in _scan_files() method
    # 3. Add type conversion in _load_saved_state() method if needed
    COLUMN_CONFIG = {
        # Status column (first column - shows if KymRoiAnalysis is loaded)
        '_kymRoiAnalysis': ColumnConfig(
            display_name='L',  # Short name for "Loaded"
            column_type=object,
            width=30,  # Narrow width for the status icon
            backend_field='_kymRoiAnalysis',
            sortable=False,
            default_value=None,
            table_visible=True,  # Make it visible in table view
            tree_visible=False,  # Keep it hidden in tree view
            widget_type='status_icon',  # Indicates this is a status icon column
            tooltip="KymRoiAnalysis Loaded Status\n● Green: Analysis object loaded in memory\n○ Gray: Analysis object not loaded",
        ),
        # Core display columns (always shown)
        'filename': ColumnConfig(
            display_name='Filename',
            column_type=str,
            width=300,  # Wider for file paths
            backend_field='filename',
            tree_visible=True,
            table_visible=True,
            default_value="",
            tooltip="The name of the .tif file",
        ),
        'date': ColumnConfig(
            display_name='Date',
            column_type=str,
            width=100,
            backend_field='date',
            tree_visible=True,
            table_visible=True,
            default_value="",
            tooltip="Date extracted from the filename (YYYYMMDD format)",
        ),
        'cell_id': ColumnConfig(
            display_name='Cell ID',
            column_type=str,
            width=120,
            backend_field='cell_id',
            tree_visible=True,
            table_visible=True,
            default_value="",
            tooltip="Cell identifier extracted from the filename",
        ),
        'region': ColumnConfig(
            display_name='Region',
            column_type=str,
            width=80,
            backend_field='region',
            tree_visible=True,
            table_visible=True,
            default_value="",
            tooltip="Region identifier extracted from the filename",
        ),
        'condition': ColumnConfig(
            display_name='Condition',
            column_type=str,
            width=100,
            backend_field='condition',
            tree_visible=True,
            table_visible=True,
            default_value="",
            tooltip="Experimental condition extracted from the filename",
        ),
        'repeat': ColumnConfig(
            display_name='Repeat',
            column_type=int,
            width=80,
            backend_field='repeat',
            tree_visible=True,
            table_visible=True,
            default_value=0,
            tooltip="Repeat number for this experimental condition",
        ),
        'numRois': ColumnConfig(
            display_name='ROIs',
            column_type=int,
            width=80,
            backend_field='numRois',
            table_visible=True,
            default_value=None,  # Unknown until analysis
            tooltip="Number of regions of interest (ROIs) defined",
        ),
        'note': ColumnConfig(
            display_name='Note',
            column_type=str,
            width=150,
            editable=True,  # Make it editable
            backend_field='note',
            table_visible=True,  # Show in table
            default_value="",
            tooltip="User-editable notes about this file",
        ),
        'show_file': ColumnConfig(
            display_name='Show',
            column_type=bool,
            width=80,
            editable=True,
            widget_type='checkbox',
            backend_field='show_file',
            tree_visible=True,
            table_visible=True,
            sortable=False,
            default_value=True,
            tooltip="Check to include this file in analysis/export operations",
        ),
        # Acquisition parameters (populated from KymRoiAnalysis)
        'msPerLine': ColumnConfig(
            display_name='ms/Line',
            column_type=float,
            width=100,
            backend_field='msPerLine',
            table_visible=True,
            default_value=None,  # Unknown until analysis
            tooltip="Time duration for each line scan (milliseconds)",
        ),
        'umPerPixel': ColumnConfig(
            display_name='μm/Pixel',
            column_type=float,
            width=100,
            backend_field='umPerPixel',
            table_visible=True,
            default_value=None,  # Unknown until analysis
            tooltip="Spatial resolution in micrometers per pixel",
        ),
        'numChannels': ColumnConfig(
            display_name='Channels',
            column_type=int,
            width=80,
            backend_field='numChannels',
            table_visible=True,
            default_value=None,  # Unknown until analysis
            tooltip="Number of acquisition channels in the image",
        ),
        'imageHeight': ColumnConfig(
            display_name='Image Height',
            column_type=int,
            width=100,
            backend_field='imageHeight',
            table_visible=True,
            default_value=None,  # Unknown until analysis
            tooltip="Height of the image in pixels",
        ),
        'imageWidth': ColumnConfig(
            display_name='Image Width',
            column_type=int,
            width=100,
            backend_field='imageWidth',
            table_visible=True,
            default_value=None,  # Unknown until analysis
            tooltip="Width of the image in pixels",
        ),
        'numLineScans': ColumnConfig(
            display_name='Line Scans',
            column_type=int,
            width=100,
            backend_field='numLineScans',
            table_visible=True,
            default_value=None,  # Unknown until analysis
            tooltip="Number of line scans in the acquisition",
        ),
        'pixelsPerLine': ColumnConfig(
            display_name='Pixels/Line',
            column_type=int,
            width=100,
            backend_field='pixelsPerLine',
            table_visible=True,
            default_value=None,  # Unknown until analysis
            tooltip="Number of pixels per line scan",
        ),
        # Hidden columns (for internal use)
        'relative_path': ColumnConfig(
            display_name='Relative Path',
            column_type=str,
            width=None,
            backend_field='relative_path',
            default_value="",
            tooltip="Internal: Relative path from root directory",
        ),
        'parent_folder': ColumnConfig(
            display_name='Parent Folder',
            column_type=str,
            width=None,
            backend_field='parent_folder',
            default_value="",
            tooltip="Internal: Parent folder name",
        ),
        'grandparent_folder': ColumnConfig(
            display_name='Grandparent Folder',
            column_type=str,
            width=None,
            backend_field='grandparent_folder',
            default_value="",
            tooltip="Internal: Grandparent folder name",
        ),
        'great_grandparent_folder': ColumnConfig(
            display_name='Great Grandparent Folder',
            column_type=str,
            width=None,
            backend_field='great_grandparent_folder',
            default_value="",
            tooltip="Internal: Great grandparent folder name",
        ),
        'error': ColumnConfig(
            display_name='Error', 
            column_type=str, 
            width=80, 
            backend_field='error',
            default_value="",
            tooltip="Error message if analysis failed",
        ),
        '_analyzed': ColumnConfig(
            display_name='Analyzed',
            column_type=bool,
            width=80,
            widget_type='status_icon',
            backend_field='_analyzed',
            table_visible=False,  # Hidden by default, can be shown for debugging
            sortable=False,
            default_value=False,
            tooltip="Internal: Whether expensive analysis has been performed",
        ),
    }

    def __init__(
        self,
        root_path: str,
        exclude_folders: Optional[List[str]] = None,
        sort_by_grandparent: bool = True,
        max_depth: int = 5,
        load_analysis_csv: bool = True,  # NEW: Control loading of saved CSV analysis
    ) -> None:
        """Initialize the TifFileBackend with a root path and configuration.
        
        This method performs the initial setup and runs the two-phase analysis:
        1. **Phase 1**: Fast file discovery and basic metadata extraction
        2. **Phase 2**: Expensive analysis of unanalyzed files
        
        The backend automatically loads any previously saved state and continues
        analysis from where it left off.
        
        Parameters
        ----------
        root_path : str
            Root directory to scan for .tif files. Must exist and be readable.
        exclude_folders : List[str], optional
            List of folder names to exclude from scanning. Useful for excluding
            output folders, temporary files, etc. Default is `["sanpy-reports-pdf"]`.
        sort_by_grandparent : bool, optional
            If `True`, sort files by grandparent folder (ignoring parent folder).
            This groups all files in the same experimental condition together.
            If `False`, sort files by parent folder. Default is `True`.
        max_depth : int, optional
            Maximum depth of folders to scan. Prevents scanning too deeply into
            nested directory structures. Default is `5`.
        load_analysis_csv : bool, optional
            If `True`, automatically load saved CSV analysis files for each .tif file
            when creating KymRoiAnalysis objects. This loads analysis results without
            loading image data. Default is `True`.
            
            When `True`, all CSV analysis files are pre-loaded during initialization
            for fast access to analysis results. Image data remains lazy-loaded.
            
        Raises
        ------
        FileNotFoundError
            If `root_path` does not exist
        PermissionError
            If `root_path` is not readable
            
        Examples
        --------
        Basic initialization:
        
        ```python
        backend = TifFileBackend("/path/to/tif/files")
        ```
        
        With custom configuration:
        
        ```python
        backend = TifFileBackend(
            root_path="/experiments/2024",
            exclude_folders=["temp", "backup"],
            sort_by_grandparent=True,
            max_depth=3,
            load_analysis_csv=True  # Load saved analysis CSV files
        )
        ```
        
        Notes
        -----
        - The backend automatically creates a `tif_file_backend_state.csv` file
          in the root directory to persist analysis results
        - Files are analyzed incrementally - only new or unanalyzed files
          will be processed during initialization
        - Use `force_reanalyze_all()` to re-analyze all files if needed
        - When `load_analysis_csv=True`, KymRoiAnalysis objects are created with
          analysis results loaded but image data not loaded (memory efficient)
        """
        # Convert root_path to Path object for cross-platform safety
        self.root_path = Path(root_path)
        self.exclude_folders = exclude_folders or ["sanpy-reports-pdf"]
        self.sort_by_grandparent = sort_by_grandparent
        self.max_depth = max_depth
        self.load_analysis_csv = load_analysis_csv  # NEW: Store the parameter

        # Initialize DataFrame with proper column structure
        self.df = pd.DataFrame(columns=list(self.COLUMN_CONFIG.keys()))

        if not self.root_path.exists():
            logger.error(f"Root path does not exist: {self.root_path}")
            return

        self._scan_files()
        self._load_saved_state()
        self._analyze_files()  # Run expensive computations on unanalyzed files

        # NEW: Pre-load all KymRoiAnalysis CSV files if enabled
        if self.load_analysis_csv:
            self._preload_all_kym_roi_analysis_csv()

        from sanpy.kym.tif_pool import TiffPool  # circular import
        self._tifPool = TiffPool(self)

    def _should_exclude_path(self, path: str) -> bool:
        """Check if path contains any excluded folders."""
        return any(excluded in path for excluded in self.exclude_folders)

    def _get_state_filepath(self) -> str:
        """Get the filepath for saving/loading state."""
        return str(self.root_path / "tif_file_backend_state.csv")

    def _ensure_all_columns_exist(self):
        """Ensure all columns from COLUMN_CONFIG exist in the DataFrame."""
        if self.df is None:
            return
            
        # Get all expected column names from COLUMN_CONFIG
        expected_columns = list(self.COLUMN_CONFIG.keys())
        
        # Add any missing columns with their default values
        for col_name in expected_columns:
            if col_name not in self.df.columns:
                default_value = self.get_column_default_value(col_name)
                self.df[col_name] = default_value
                logger.debug(f"Added missing column '{col_name}' with default value: {default_value}")

    def _load_saved_state(self):
        """Load saved state from CSV file if it exists."""
        state_filepath = self._get_state_filepath()
        if os.path.exists(state_filepath):
            try:
                loaded_df = pd.read_csv(state_filepath)
                if len(self.df) > 0 and len(loaded_df) > 0:
                    common_cols = [
                        col for col in loaded_df.columns
                        if col in self.df.columns and col in self.COLUMN_CONFIG and col != '_analyzed'
                    ]
                    if 'relative_path' not in loaded_df.columns:
                        logger.error(f"relative_path column missing from saved state file: {state_filepath}")
                        return
                    if common_cols:
                        update_cols = ['relative_path'] + [col for col in common_cols if col != 'relative_path']
                        update_df = loaded_df[update_cols].copy()
                        if 'repeat' in common_cols:
                            update_df['repeat'] = pd.to_numeric(update_df['repeat'], errors='coerce').fillna(0).astype(int)
                        # Ensure integer columns are properly typed
                        for col in ['numChannels', 'imageHeight', 'imageWidth', 'numLineScans', 'pixelsPerLine', 'numRois']:
                            if col in common_cols:
                                update_df[col] = pd.to_numeric(update_df[col], errors='coerce').fillna(0).astype(int)
                        for col in ['show_file']:
                            if col in common_cols:
                                update_df[col] = update_df[col].astype(int).astype(bool)
                        for col in common_cols:
                            if col == 'relative_path':
                                continue
                            mapping_series = update_df.set_index('relative_path')[col]
                            mapped_values = self.df['relative_path'].map(mapping_series)
                            updated_column = mapped_values.fillna(self.df[col])
                            if col == 'show_file':
                                updated_column = updated_column.map(lambda x: bool(x))
                            elif col == 'repeat':
                                updated_column = pd.to_numeric(updated_column, errors='coerce').fillna(0).astype(int)
                            elif col in ['numChannels', 'imageHeight', 'imageWidth', 'numLineScans', 'pixelsPerLine', 'numRois']:
                                updated_column = pd.to_numeric(updated_column, errors='coerce').fillna(0).astype(int)
                            elif col in ['parent_folder', 'grandparent_folder', 'great_grandparent_folder']:
                                updated_column = updated_column.astype(str).replace('nan', '')
                            elif col == 'note':
                                updated_column = updated_column.astype(str).replace('nan', '')
                            elif hasattr(updated_column, 'infer_objects') and updated_column.dtype == 'object':
                                updated_column = updated_column.infer_objects(copy=False)
                            self.df[col] = updated_column
                        
                        # Handle _analyzed column - preserve saved status if it exists, otherwise set to False
                        if '_analyzed' in loaded_df.columns:
                            # Load saved _analyzed status
                            analyzed_series = loaded_df.set_index('relative_path')['_analyzed']
                            analyzed_values = self.df['relative_path'].map(analyzed_series)
                            # Convert to boolean (1/0 -> True/False)
                            self.df['_analyzed'] = analyzed_values.fillna(False).astype(bool)
                            # logger.info(f"Loaded _analyzed status from saved state")
                        else:
                            # No saved _analyzed status, set all to False
                            self.df['_analyzed'] = False
                            # logger.info(f"No saved _analyzed status found, setting all to False")
                        
                        # logger.info(f"Loaded state from: {state_filepath}")
                    else:
                        logger.warning(f"No matching columns found in saved state file: {state_filepath}")
                        # Set _analyzed to False if no saved state was loaded
                        self.df['_analyzed'] = False
            except (pd.errors.EmptyDataError, pd.errors.ParserError, ValueError, OSError) as e:
                logger.error(f"Error loading state from {state_filepath}: {e}")
                # Set _analyzed to False on error
                self.df['_analyzed'] = False
            except Exception as e:
                logger.error(f"Unexpected error loading state from {state_filepath}: {e}")
                # Set _analyzed to False on error
                self.df['_analyzed'] = False
                raise
        else:
            # No saved state file exists, ensure all columns exist and set _analyzed to False
            self._ensure_all_columns_exist()
            self.df['_analyzed'] = False

    def _scan_files(self):
        """Scan for .tif files and populate the dataframe with basic metadata only."""
        logger.info(
            f"Scanning for .tif files in: {self.root_path} (max depth: {self.max_depth})"
        )

        file_data = []

        try:
            for root, dirs, files in os.walk(str(self.root_path)):
                # Calculate current depth relative to root_path using pathlib
                root_path = Path(root)
                current_depth = len(root_path.relative_to(self.root_path).parts)

                # Skip if this path should be excluded
                if self._should_exclude_path(str(root_path)):
                    continue

                # Limit depth by modifying dirs list in-place
                if current_depth >= self.max_depth:
                    # Clear dirs list to prevent os.walk from going deeper
                    dirs.clear()
                    logger.debug(f"Reached max depth ({self.max_depth}) at: {root_path}")

                # Filter for .tif files and sort them
                tif_files = sorted([f for f in files if f.lower().endswith('.tif')])

                for _idx, tif_file in enumerate(tif_files):
                    full_path = root_path / tif_file

                    # Calculate relative path using pathlib
                    try:
                        relative_path = full_path.relative_to(self.root_path).as_posix()
                    except ValueError:
                        # Handle case where paths are on different drives
                        relative_path = str(full_path)

                    # Extract folder hierarchy using pathlib
                    rel_path_obj = Path(relative_path)
                    path_parts = rel_path_obj.parts

                    if len(path_parts) >= 4:
                        # We have enough levels for the full hierarchy
                        parent_folder = path_parts[
                            -2
                        ]  # Folder containing the .tif file
                        grandparent_folder = path_parts[-3]
                        great_grandparent_folder = path_parts[-4]
                    elif len(path_parts) == 3:
                        # Three levels: great_grandparent/grandparent/file.tif
                        parent_folder = path_parts[-2]
                        grandparent_folder = path_parts[-3]
                        great_grandparent_folder = ""
                    elif len(path_parts) == 2:
                        # Two levels: grandparent/file.tif
                        parent_folder = path_parts[-2]
                        grandparent_folder = ""
                        great_grandparent_folder = ""
                    else:
                        # File is directly in root
                        parent_folder = ""
                        grandparent_folder = ""
                        great_grandparent_folder = ""

                    # Basic file data - no expensive computations here
                    file_data.append(
                        {
                            'relative_path': relative_path,
                            'filename': tif_file,
                            'parent_folder': parent_folder,
                            'grandparent_folder': grandparent_folder,
                            'great_grandparent_folder': great_grandparent_folder,
                            'date': self.get_column_default_value('date'),
                            'cell_id': self.get_column_default_value('cell_id'),
                            'region': self.get_column_default_value('region'),
                            'condition': self.get_column_default_value('condition'),
                            'repeat': self.get_column_default_value('repeat'),
                            'error': self.get_column_default_value('error'),
                            'show_file': self.get_column_default_value('show_file'),
                            'note': self.get_column_default_value('note'),
                            '_kymRoiAnalysis': self.get_column_default_value('_kymRoiAnalysis'),
                            '_analyzed': self.get_column_default_value('_analyzed'),
                            # Acquisition parameters - will be populated in _analyze_files()
                            'msPerLine': self.get_column_default_value('msPerLine'),
                            'umPerPixel': self.get_column_default_value('umPerPixel'),
                            'numChannels': self.get_column_default_value('numChannels'),
                            'imageHeight': self.get_column_default_value('imageHeight'),
                            'imageWidth': self.get_column_default_value('imageWidth'),
                            'numLineScans': self.get_column_default_value('numLineScans'),
                            'pixelsPerLine': self.get_column_default_value('pixelsPerLine'),
                            'numRois': self.get_column_default_value('numRois'),
                        }
                    )
        except PermissionError as e:
            logger.error(f"Permission denied accessing {self.root_path}: {e}")
        except (OSError, IOError) as e:
            logger.error(f"File system error scanning {self.root_path}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error scanning {self.root_path}: {e}")
            # Re-raise unexpected errors to avoid masking bugs
            raise

        # Create DataFrame from collected data
        self.df = pd.DataFrame(file_data)
        # Ensure 'date' column is always str type
        if 'date' in self.df.columns:
            self.df['date'] = self.df['date'].astype(str)

        # Sort by grandparent_folder first, then by filename
        # This groups all files in the same grandparent folder together
        if len(self.df) > 0:
            if self.sort_by_grandparent:
                self.df = self.df.sort_values(
                    ['great_grandparent_folder', 'grandparent_folder', 'filename']
                )
            else:
                self.df = self.df.sort_values(['parent_folder', 'filename'])

        if len(self.df) > 0:
            logger.info(f"Found {len(self.df)} .tif files")
        else:
            logger.warning("No .tif files found")
            # Ensure all columns exist even when no files are found
            self._ensure_all_columns_exist()

    def _extract_acquisition_parameters(self, tif_path: Path) -> Dict[str, Any]:
        """
        Extract acquisition parameters from analysis files without loading full KymRoiAnalysis objects.
        
        This method reads the analysis files directly to get acquisition parameters
        without the memory overhead of loading full KymRoiAnalysis objects.
        
        Parameters
        ----------
        tif_path : Path
            Path to the .tif file
            
        Returns
        -------
        Dict[str, Any]
            Dictionary of acquisition parameters, or empty dict if extraction fails
        """
        try:
            # Import here to avoid circular imports
            # from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis
            
            # Create KymRoiAnalysis in analysis_only mode to avoid loading image data
            kym_analysis = KymRoiAnalysis(path=str(tif_path), analysis_only=True, loadImgData=False)
            
            ms_per_line = None
            if kym_analysis.secondsPerLine is not None:
                ms_per_line = float(kym_analysis.secondsPerLine) * 1000.0
            params = {
                'msPerLine': ms_per_line,
                'umPerPixel': kym_analysis.umPerPixel,
                'numChannels': int(kym_analysis.numChannels),
                'imageHeight': int(kym_analysis.header.getParam('imageHeight')),
                'imageWidth': int(kym_analysis.header.getParam('imageWidth')),
                'numLineScans': int(kym_analysis.numLineScans),
                'pixelsPerLine': int(kym_analysis.numPixelsPerLine),
                'numRois': int(kym_analysis.numRoi),
            }
            
            return params
            
        except Exception as e:
            logger.warning(f"Failed to extract acquisition parameters from {tif_path}: {e}")
            return {}

    def _analyze_files(self, force_reanalyze: bool = False):
        """
        Run expensive computations on .tif files that haven't been analyzed yet.

        This method should be called after _scan_files() to populate expensive columns.
        Each file is analyzed only once unless force_reanalyze=True.

        Parameters
        ----------
        force_reanalyze : bool, optional
            If True, re-analyze all files even if they've been analyzed before.
            Default is False.
        """
        if self.df is None or len(self.df) == 0:
            logger.warning("No files to analyze")
            return

        # Find files that need analysis
        if force_reanalyze:
            files_to_analyze = self.df
            logger.info(f"Force re-analyzing all {len(files_to_analyze)} files")
        else:
            files_to_analyze = self.df[~self.df['_analyzed']]
            logger.info(
                f"Analyzing {len(files_to_analyze)} files that haven't been analyzed yet"
            )

        if len(files_to_analyze) == 0:
            logger.info("No files need analysis")
            return

        for idx, row in files_to_analyze.iterrows():
            # Define default values for all columns that might be set
            default_values = self._get_analysis_default_values(error_message="")
            
            try:
                logger.debug(f"Analyzing file: {row['filename']}")

                # Parse filename with TifInfo (expensive operation)
                tif_info = TifInfo.from_filename(row['filename'])

                # Ensure 'date' column is str type before assignment
                self.df['date'] = self.df['date'].astype(str)

                # Update the DataFrame with analysis results
                self.df.at[idx, 'date'] = str(tif_info.date)
                self.df.at[idx, 'cell_id'] = tif_info.cellid
                self.df.at[idx, 'region'] = tif_info.region
                self.df.at[idx, 'condition'] = tif_info.condition
                self.df.at[idx, 'repeat'] = tif_info.repeat
                self.df.at[idx, 'error'] = tif_info.error

                # Mark as analyzed
                self.df.at[idx, '_analyzed'] = True

                # Extract acquisition parameters without loading full KymRoiAnalysis objects
                tif_path = self.resolve_path(row['relative_path'])
                acquisition_params = self._extract_acquisition_parameters(tif_path)
                
                # Update acquisition parameters if extraction was successful
                if acquisition_params:
                    self.df.at[idx, 'msPerLine'] = acquisition_params['msPerLine']
                    self.df.at[idx, 'umPerPixel'] = acquisition_params['umPerPixel']
                    self.df.at[idx, 'numChannels'] = acquisition_params['numChannels']
                    self.df.at[idx, 'imageHeight'] = acquisition_params['imageHeight']
                    self.df.at[idx, 'imageWidth'] = acquisition_params['imageWidth']
                    self.df.at[idx, 'numLineScans'] = acquisition_params['numLineScans']
                    self.df.at[idx, 'pixelsPerLine'] = acquisition_params['pixelsPerLine']
                    self.df.at[idx, 'numRois'] = acquisition_params['numRois']
                    logger.debug(f"Extracted acquisition parameters for {row['filename']}")
                else:
                    logger.debug(f"Failed to extract acquisition parameters for {row['filename']}")

            except (ValueError, AttributeError, TypeError) as e:
                # If TifInfo parsing fails, use default values and log the error
                logger.warning(f"Failed to analyze filename '{row['filename']}': {e}")
                default_values = self._get_analysis_default_values(error_message=str(e))
                default_values['_analyzed'] = True  # Mark as analyzed to avoid retrying
                
                # Apply filename-related default values
                self._apply_default_values(idx, default_values)
                
                # Still try to extract acquisition parameters even if filename parsing failed
                # Acquisition parameters come from the TIF file, not the filename
                try:
                    tif_path = self.resolve_path(row['relative_path'])
                    acquisition_params = self._extract_acquisition_parameters(tif_path)
                    
                    # Update acquisition parameters if extraction was successful
                    if acquisition_params:
                        self.df.at[idx, 'msPerLine'] = acquisition_params['msPerLine']
                        self.df.at[idx, 'umPerPixel'] = acquisition_params['umPerPixel']
                        self.df.at[idx, 'numChannels'] = acquisition_params['numChannels']
                        self.df.at[idx, 'imageHeight'] = acquisition_params['imageHeight']
                        self.df.at[idx, 'imageWidth'] = acquisition_params['imageWidth']
                        self.df.at[idx, 'numLineScans'] = acquisition_params['numLineScans']
                        self.df.at[idx, 'pixelsPerLine'] = acquisition_params['pixelsPerLine']
                        self.df.at[idx, 'numRois'] = acquisition_params['numRois']
                        logger.debug(f"Extracted acquisition parameters for {row['filename']} (despite filename parsing failure)")
                    else:
                        logger.debug(f"Failed to extract acquisition parameters for {row['filename']} (despite filename parsing failure)")
                except Exception as acq_error:
                    logger.warning(f"Failed to extract acquisition parameters for {row['filename']}: {acq_error}")

            except Exception as e:
                # Log unexpected errors but continue processing other files
                logger.error(
                    f"Unexpected error analyzing file '{row['filename']}': {e}"
                )
                default_values = self._get_analysis_default_values(error_message=str(e))
                default_values['_analyzed'] = True  # Mark as analyzed to avoid retrying
                
                # Apply all default values
                self._apply_default_values(idx, default_values)

        logger.info(f"Completed analysis of {len(files_to_analyze)} files")

    def _preload_all_kym_roi_analysis_csv(self):
        """
        Pre-load all KymRoiAnalysis CSV files during initialization.
        
        This method loads all saved CSV analysis files for each .tif file in the backend,
        but does NOT load the actual TIF image data. This provides fast access to analysis
        results while keeping memory usage low.
        
        Only called when load_analysis_csv=True during initialization.
        """
        if self.df is None or len(self.df) == 0:
            logger.info("No files to pre-load CSV analysis for")
            return
            
        logger.info(f"Pre-loading KymRoiAnalysis CSV files for {len(self.df)} files...")
        
        loaded_count = 0
        failed_count = 0
        
        for idx, row in self.df.iterrows():
            try:
                # Get the file path for this row
                relative_path = row['relative_path']
                tif_path = self.resolve_path(relative_path)
                
                # Create KymRoiAnalysis with CSV analysis loaded but no image data
                kym_analysis = KymRoiAnalysis(path=str(tif_path), analysis_only=True, loadImgData=False)
                
                # Cache the KymRoiAnalysis object
                self.df.at[idx, '_kymRoiAnalysis'] = kym_analysis
                loaded_count += 1
                
                if loaded_count % 50 == 0:  # Log progress every 50 files
                    logger.info(f"Pre-loaded {loaded_count}/{len(self.df)} CSV analysis files...")
                    
            except Exception as e:
                logger.warning(f"Failed to pre-load CSV analysis for {row['filename']}: {e}")
                failed_count += 1
                # Set to None to indicate failure
                self.df.at[idx, '_kymRoiAnalysis'] = None
        
        logger.info(f"Pre-loading complete: {loaded_count} successful, {failed_count} failed")

    def _get_analysis_default_values(self, error_message: str = "") -> Dict[str, Any]:
        """
        Get default values for all analysis columns from COLUMN_CONFIG.
        
        Parameters
        ----------
        error_message : str, optional
            Error message to set in the 'error' column
            
        Returns
        -------
        Dict[str, Any]
            Dictionary of default values for all analysis columns
        """
        default_values = {}
        
        # Get default values from COLUMN_CONFIG for all columns
        for col_name, config in self.COLUMN_CONFIG.items():
            default_values[col_name] = config.default_value
        
        # Override error message if provided
        if error_message:
            default_values['error'] = error_message
            
        return default_values

    def _apply_default_values(self, idx: int, default_values: Dict[str, Any]):
        """
        Apply default values to a specific row in the DataFrame.
        
        Parameters
        ----------
        idx : int
            Row index in the DataFrame
        default_values : Dict[str, Any]
            Dictionary of column names and their default values
        """
        for col, value in default_values.items():
            if col in self.df.columns:
                self.df.at[idx, col] = value

    def get(
        self, item_type: str, **kwargs
    ) -> Union[List[str], Dict[str, int], List[str], int, pd.DataFrame]:
        """Get data from the backend based on the specified item type.
        
        This is the primary method for retrieving data from the backend. It provides
        various ways to access file information, counts, and filtered data.
        
        Parameters
        ----------
        item_type : str
            Type of data to retrieve. Valid options:
            
            - `'files'`: Get full paths of checked files (files with `show_file=True`)
            - `'file_count'`: Get total number of files in the backend
            - `'condition_counts'`: Get counts of files by experimental condition
            - `'repeat_counts'`: Get counts of files by repeat number
            - `'unique_conditions'`: Get list of unique experimental conditions
            - `'unique_repeats'`: Get list of unique repeat numbers
            - `'filter_by_condition'`: Filter files by specific condition (requires `condition` parameter)
            - `'filter_by_repeat'`: Filter files by specific repeat (requires `repeat` parameter)
            
        **kwargs
            Additional parameters for specific item types:
            
            - `condition` (str): Required for `'filter_by_condition'` - the condition to filter by
            - `repeat` (int): Required for `'filter_by_repeat'` - the repeat number to filter by
            
        Returns
        -------
        Union[List[str], Dict[str, int], List[str], int, pd.DataFrame]
            The requested data, type depends on `item_type`:
            
            - `List[str]`: For `'files'`, `'unique_conditions'`, `'unique_repeats'`
            - `Dict[str, int]`: For `'condition_counts'`, `'repeat_counts'`
            - `int`: For `'file_count'`
            - `pd.DataFrame`: For `'filter_by_condition'`, `'filter_by_repeat'`
            
        Raises
        ------
        ValueError
            If `item_type` is invalid or required parameters are missing
            
        Examples
        --------
        Get all checked files:
        
        ```python
        files = backend.get('files')
        print(f"Found {len(files)} checked files")
        ```
        
        Get file counts by condition:
        
        ```python
        condition_counts = backend.get('condition_counts')
        # Returns: {'Control': 10, 'Treatment': 15, 'FCCP': 8}
        ```
        
        Get unique conditions:
        
        ```python
        conditions = backend.get('unique_conditions')
        # Returns: ['Control', 'Treatment', 'FCCP']
        ```
        
        Filter by specific condition:
        
        ```python
        control_files = backend.get('filter_by_condition', condition='Control')
        # Returns DataFrame with only Control files
        ```
        
        Get total file count:
        
        ```python
        total_files = backend.get('file_count')
        print(f"Total files: {total_files}")
        ```
        
        Notes
        -----
        - The `'files'` item type only returns files where `show_file=True`
        - Filter methods return full DataFrames that can be further processed
        - Count methods return dictionaries for easy iteration and display
        - All paths returned by `'files'` are absolute paths
        """
        if self.df is None or len(self.df) == 0:
            return (
                []
                if item_type in ['files', 'unique_conditions', 'unique_repeats']
                else {}
            )
        
        if item_type == 'files':
            # Construct full paths from relative paths
            relative_paths = self.df[self.df['show_file']]['relative_path'].tolist()
            return [self.resolve_path(rel_path) for rel_path in relative_paths]
        
        elif item_type == 'file_count':
            return len(self.df)
        
        elif item_type == 'condition_counts':
            return self.df['condition'].value_counts().to_dict()
        
        elif item_type == 'repeat_counts':
            return self.df['repeat'].value_counts().to_dict()
        
        elif item_type == 'unique_conditions':
            return self.df['condition'].unique().tolist()
        
        elif item_type == 'unique_repeats':
            return sorted(self.df['repeat'].unique().tolist())
        
        elif item_type == 'filter_by_condition':
            condition = kwargs.get('condition')
            if condition is None:
                raise ValueError("condition parameter required for filter_by_condition")
            return self.df[self.df['condition'] == condition]
        
        elif item_type == 'filter_by_repeat':
            repeat = kwargs.get('repeat')
            if repeat is None:
                raise ValueError("repeat parameter required for filter_by_repeat")
            return self.df[self.df['repeat'] == repeat]
        
        else:
            raise ValueError(
                f"Invalid item_type: {item_type}. Valid options: ['files', 'file_count', 'condition_counts', 'repeat_counts', 'unique_conditions', 'unique_repeats', 'filter_by_condition', 'filter_by_repeat']"
            )

    def set_checked(self, item_type: str, identifier: str, checked: bool):
        """
        Set checkbox state for individual files.

        Parameters
        ----------
        item_type : str
            Type of item to set. Only 'file' is supported.
        identifier : str
            The full path of the file
        checked : bool
            Whether the file should be checked
        """
        if self.df is None:
            return

        if item_type == 'file':
            # Convert full path to relative path for matching using pathlib
            identifier_path = Path(identifier)
            if identifier_path.is_absolute():
                # If it's an absolute path, convert to relative path
                try:
                    relative_path = identifier_path.relative_to(self.root_path).as_posix()
                except ValueError:
                    # Handle case where paths are on different drives
                    relative_path = identifier_path.as_posix()
            else:
                relative_path = identifier_path.as_posix()

            mask = self.df['relative_path'] == relative_path
            if mask.any():
                # Ensure we're setting a Python bool, not numpy.bool_
                self.df.loc[mask, 'show_file'] = bool(checked)
                # Force the entire column to be native Python bool
                self.df['show_file'] = (
                    self.df['show_file'].map(lambda x: bool(x)).astype(object)
                )
                # Auto-save state after modification
                self._auto_save_state()
        else:
            raise ValueError(
                f"Invalid item_type: {item_type}. Only 'file' is supported."
            )

    def refresh(self):
        """Refresh the data by detecting file system changes and updating incrementally."""
        logger.info("Refreshing file data with incremental updates")

        if self.df is None or len(self.df) == 0:
            # If no existing data, do a full scan
            self._scan_files()
            self._analyze_files()
            return

        # Store current state for comparison
        current_files = set(self.df['relative_path'].tolist())

        # Get current file system state
        current_fs_files = self._get_current_filesystem_files()

        # Find added and removed files
        added_files = current_fs_files - current_files
        removed_files = current_files - current_fs_files

        logger.info(
            f"File system changes detected: {len(added_files)} added, {len(removed_files)} removed"
        )

        # Remove deleted files
        if removed_files:
            self.df = self.df[~self.df['relative_path'].isin(removed_files)]
            logger.info(f"Removed {len(removed_files)} deleted files from DataFrame")

        # Add new files
        if added_files:
            new_files_data = self._scan_specific_files(added_files)
            if new_files_data:
                new_df = pd.DataFrame(new_files_data)
                self.df = pd.concat([self.df, new_df], ignore_index=True)

                # Re-sort the DataFrame
                if self.sort_by_grandparent:
                    self.df = self.df.sort_values(
                        ['great_grandparent_folder', 'grandparent_folder', 'filename']
                    )
                else:
                    self.df = self.df.sort_values(['parent_folder', 'filename'])

                # Analyze only the new files
                self._analyze_specific_files(added_files)
                logger.info(f"Added and analyzed {len(new_files_data)} new files")

        # Auto-save state after changes
        if added_files or removed_files:
            self._auto_save_state()

    def _get_current_filesystem_files(self) -> set:
        """Get the current set of .tif files in the filesystem."""
        current_files = set()

        try:
            for root, dirs, files in os.walk(str(self.root_path)):
                # Calculate current depth relative to root_path using pathlib
                root_path = Path(root)
                current_depth = len(root_path.relative_to(self.root_path).parts)

                # Skip if this path should be excluded
                if self._should_exclude_path(str(root_path)):
                    continue

                # Limit depth by modifying dirs list in-place
                if current_depth >= self.max_depth:
                    dirs.clear()
                    continue

                # Filter for .tif files
                tif_files = [f for f in files if f.lower().endswith('.tif')]

                for tif_file in tif_files:
                    full_path = root_path / tif_file
                    try:
                        relative_path = full_path.relative_to(self.root_path).as_posix()
                        current_files.add(relative_path)
                    except ValueError:
                        # Handle case where paths are on different drives
                        current_files.add(full_path.as_posix())

        except (PermissionError, OSError, IOError) as e:
            logger.error(f"Error scanning filesystem: {e}")

        return current_files

    def _scan_specific_files(self, relative_paths: set) -> List[Dict[str, Any]]:
        """Scan specific files and return their basic metadata."""
        file_data = []

        for relative_path in relative_paths:
            try:
                full_path = self.root_path / relative_path

                # Extract folder hierarchy using pathlib
                rel_path_obj = Path(relative_path)
                path_parts = rel_path_obj.parts

                if len(path_parts) >= 4:
                    parent_folder = path_parts[-2]
                    grandparent_folder = path_parts[-3]
                    great_grandparent_folder = path_parts[-4]
                elif len(path_parts) == 3:
                    parent_folder = path_parts[-2]
                    grandparent_folder = path_parts[-3]
                    great_grandparent_folder = ""
                elif len(path_parts) == 2:
                    parent_folder = path_parts[-2]
                    grandparent_folder = ""
                    great_grandparent_folder = ""
                else:
                    parent_folder = ""
                    grandparent_folder = ""
                    great_grandparent_folder = ""

                filename = rel_path_obj.name

                # Basic file data - no expensive computations here
                file_data.append(
                    {
                        'relative_path': relative_path,
                        'filename': filename,
                        'parent_folder': parent_folder,
                        'grandparent_folder': grandparent_folder,
                        'great_grandparent_folder': great_grandparent_folder,
                        'date': self.get_column_default_value('date'),
                        'cell_id': self.get_column_default_value('cell_id'),
                        'region': self.get_column_default_value('region'),
                        'condition': self.get_column_default_value('condition'),
                        'repeat': self.get_column_default_value('repeat'),
                        'error': self.get_column_default_value('error'),
                        'show_file': self.get_column_default_value('show_file'),
                        'note': self.get_column_default_value('note'),
                        '_kymRoiAnalysis': self.get_column_default_value('_kymRoiAnalysis'),
                        '_analyzed': self.get_column_default_value('_analyzed'),
                        # Acquisition parameters - will be populated in _analyze_files()
                        'msPerLine': self.get_column_default_value('msPerLine'),
                        'umPerPixel': self.get_column_default_value('umPerPixel'),
                        'numChannels': self.get_column_default_value('numChannels'),
                        'imageHeight': self.get_column_default_value('imageHeight'),
                        'imageWidth': self.get_column_default_value('imageWidth'),
                        'numLineScans': self.get_column_default_value('numLineScans'),
                        'pixelsPerLine': self.get_column_default_value('pixelsPerLine'),
                        'numRois': self.get_column_default_value('numRois'),
                    }
                )

            except Exception as e:
                logger.error(f"Error scanning file {relative_path}: {e}")

        return file_data

    def _analyze_specific_files(self, relative_paths: set):
        """Analyze specific files that haven't been analyzed yet."""
        if self.df is None or len(self.df) == 0:
            return

        # Find files that need analysis
        files_to_analyze = self.df[
            (self.df['relative_path'].isin(relative_paths)) & (~self.df['_analyzed'])
        ]

        if len(files_to_analyze) == 0:
            return

        logger.info(f"Analyzing {len(files_to_analyze)} specific files")

        for idx, row in files_to_analyze.iterrows():
            # Define default values for all columns that might be set
            default_values = self._get_analysis_default_values(error_message="")
            
            try:
                logger.debug(f"Analyzing file: {row['filename']}")

                # Parse filename with TifInfo (expensive operation)
                tif_info = TifInfo.from_filename(row['filename'])

                # Ensure 'date' column is str type before assignment
                self.df['date'] = self.df['date'].astype(str)

                # Update the DataFrame with analysis results
                self.df.at[idx, 'date'] = str(tif_info.date)
                self.df.at[idx, 'cell_id'] = tif_info.cellid
                self.df.at[idx, 'region'] = tif_info.region
                self.df.at[idx, 'condition'] = tif_info.condition
                self.df.at[idx, 'repeat'] = tif_info.repeat
                self.df.at[idx, 'error'] = tif_info.error

                # Mark as analyzed
                self.df.at[idx, '_analyzed'] = True

                # Extract acquisition parameters without loading full KymRoiAnalysis objects
                tif_path = self.resolve_path(row['relative_path'])
                acquisition_params = self._extract_acquisition_parameters(tif_path)
                
                # Update acquisition parameters if extraction was successful
                if acquisition_params:
                    self.df.at[idx, 'msPerLine'] = acquisition_params['msPerLine']
                    self.df.at[idx, 'umPerPixel'] = acquisition_params['umPerPixel']
                    self.df.at[idx, 'numChannels'] = acquisition_params['numChannels']
                    self.df.at[idx, 'imageHeight'] = acquisition_params['imageHeight']
                    self.df.at[idx, 'imageWidth'] = acquisition_params['imageWidth']
                    self.df.at[idx, 'numLineScans'] = acquisition_params['numLineScans']
                    self.df.at[idx, 'pixelsPerLine'] = acquisition_params['pixelsPerLine']
                    self.df.at[idx, 'numRois'] = acquisition_params['numRois']
                    logger.debug(f"Extracted acquisition parameters for {row['filename']}")
                else:
                    logger.debug(f"Failed to extract acquisition parameters for {row['filename']}")

            except (ValueError, AttributeError, TypeError) as e:
                # If TifInfo parsing fails, use default values and log the error
                logger.warning(f"Failed to analyze filename '{row['filename']}': {e}")
                default_values = self._get_analysis_default_values(error_message=str(e))
                default_values['_analyzed'] = True  # Mark as analyzed to avoid retrying
                
                # Apply filename-related default values
                self._apply_default_values(idx, default_values)
                
                # Still try to extract acquisition parameters even if filename parsing failed
                # Acquisition parameters come from the TIF file, not the filename
                try:
                    tif_path = self.resolve_path(row['relative_path'])
                    acquisition_params = self._extract_acquisition_parameters(tif_path)
                    
                    # Update acquisition parameters if extraction was successful
                    if acquisition_params:
                        self.df.at[idx, 'msPerLine'] = acquisition_params['msPerLine']
                        self.df.at[idx, 'umPerPixel'] = acquisition_params['umPerPixel']
                        self.df.at[idx, 'numChannels'] = acquisition_params['numChannels']
                        self.df.at[idx, 'imageHeight'] = acquisition_params['imageHeight']
                        self.df.at[idx, 'imageWidth'] = acquisition_params['imageWidth']
                        self.df.at[idx, 'numLineScans'] = acquisition_params['numLineScans']
                        self.df.at[idx, 'pixelsPerLine'] = acquisition_params['pixelsPerLine']
                        self.df.at[idx, 'numRois'] = acquisition_params['numRois']
                        logger.debug(f"Extracted acquisition parameters for {row['filename']} (despite filename parsing failure)")
                    else:
                        logger.debug(f"Failed to extract acquisition parameters for {row['filename']} (despite filename parsing failure)")
                except Exception as acq_error:
                    logger.warning(f"Failed to extract acquisition parameters for {row['filename']}: {acq_error}")

            except Exception as e:
                # Log unexpected errors but continue processing other files
                logger.error(
                    f"Unexpected error analyzing file '{row['filename']}': {e}"
                )
                default_values = self._get_analysis_default_values(error_message=str(e))
                default_values['_analyzed'] = True  # Mark as analyzed to avoid retrying
                
                # Apply all default values
                self._apply_default_values(idx, default_values)

    def set_max_depth(self, max_depth: int, refresh_scan: bool = True):
        """
        Set the maximum depth for folder scanning.

        Parameters
        ----------
        max_depth : int
            Maximum depth of folders to scan
        refresh_scan : bool, optional
            If True, refresh the scan with the new depth limit. Default is True.
        """
        if max_depth < 0:
            raise ValueError("max_depth must be non-negative")

        self.max_depth = max_depth
        logger.info(f"Set max_depth to {max_depth}")

        if refresh_scan:
            self.refresh()

    def force_reanalyze_all(self) -> None:
        """Force re-analysis of all .tif files in the backend.
        
        This method re-runs expensive computations on all files, even if they've been
        analyzed before. This is useful when you've added new analysis columns, updated
        the analysis logic, or want to refresh all data.
        
        **What gets re-analyzed:**
        
        - Filename parsing with `TifInfo`
        - Acquisition parameter extraction from `KymRoiAnalysis`
        - All metadata and computed columns
        
        **Performance considerations:**
        
        - This can be slow for large datasets
        - Each file requires loading `KymRoiAnalysis` in analysis-only mode
        - Progress can be monitored with `get_analysis_status()`
        
        Examples
        --------
        Force re-analysis of all files:
        
        ```python
        backend.force_reanalyze_all()
        print("Re-analysis complete")
        ```
        
        Check progress during re-analysis:
        
        ```python
        status = backend.get_analysis_status()
        print(f"Progress: {status['analyzed']}/{status['total']} files analyzed")
        ```
        
        Notes
        -----
        - This method automatically saves state after completion
        - All files will have `_analyzed=True` after completion
        - Use `analyze_unanalyzed_files()` for incremental analysis instead
        - Consider the performance impact on large datasets
        """
        logger.info("Force re-analyzing all files")
        self._analyze_files(force_reanalyze=True)
        self._auto_save_state()  # Auto-save the updated analysis results

    def analyze_unanalyzed_files(self) -> None:
        """Analyze only files that haven't been analyzed yet.
        
        This method runs expensive computations only on files where `_analyzed=False`.
        This is the default behavior and is called automatically during initialization.
        
        **When to use:**
        
        - After adding new files to the directory
        - When resuming analysis after interruption
        - For incremental analysis of large datasets
        
        **Performance benefits:**
        
        - Only processes new or unanalyzed files
        - Much faster than `force_reanalyze_all()` for large datasets
        - Preserves existing analysis results
        
        Examples
        --------
        Analyze only unanalyzed files:
        
        ```python
        backend.analyze_unanalyzed_files()
        ```
        
        Check what needs analysis:
        
        ```python
        status = backend.get_analysis_status()
        if status['unanalyzed'] > 0:
            print(f"Need to analyze {status['unanalyzed']} files")
            backend.analyze_unanalyzed_files()
        ```
        
        Notes
        -----
        - This method automatically saves state after completion
        - Only files with `_analyzed=False` will be processed
        - Use `force_reanalyze_all()` to re-analyze all files
        - Safe to call multiple times - only unanalyzed files are processed
        """
        logger.info("Analyzing unanalyzed files")
        self._analyze_files(force_reanalyze=False)
        self._auto_save_state()  # Auto-save the updated analysis results

    def get_analysis_status(self) -> Dict[str, int]:
        """
        Get the current analysis status.

        Returns
        -------
        Dict[str, int]
            Dictionary with counts of analyzed and unanalyzed files
        """
        if self.df is None or len(self.df) == 0:
            return {'total': 0, 'analyzed': 0, 'unanalyzed': 0}

        total = len(self.df)
        analyzed = self.df['_analyzed'].sum() if '_analyzed' in self.df.columns else 0
        unanalyzed = total - analyzed

        return {'total': total, 'analyzed': analyzed, 'unanalyzed': unanalyzed}

    def _auto_save_state(self):
        """Automatically save the current state without verbose logging."""
        if len(self.df) > 0:
            filepath = self._get_state_filepath()
            save_df = self.df.copy()
            if '_kymRoiAnalysis' in save_df.columns:
                save_df = save_df.drop(columns=['_kymRoiAnalysis'])
            
            # Use COLUMN_CONFIG to determine type conversions
            for col_name, config in self.COLUMN_CONFIG.items():
                if col_name in save_df.columns:
                    column_type = config.column_type
                    if column_type == bool:
                        save_df[col_name] = save_df[col_name].astype(bool).astype(int)
                    elif column_type == int:
                        save_df[col_name] = pd.to_numeric(save_df[col_name], errors='coerce').fillna(0).astype(int)
                    elif column_type == float:
                        save_df[col_name] = pd.to_numeric(save_df[col_name], errors='coerce').fillna(0.0).astype(float)
            
            save_df.to_csv(filepath, index=False)
            logger.debug(f"Auto-saved state to: {filepath}")
            return filepath
        return None

    def save_state(self, filepath: str = None):
        """Save the current dataframe state to a CSV file."""
        if len(self.df) > 0:
            if filepath is None:
                filepath = self._get_state_filepath()

            save_df = self.df.copy()
            if '_kymRoiAnalysis' in save_df.columns:
                save_df = save_df.drop(columns=['_kymRoiAnalysis'])
            # Note: _analyzed column is now saved to preserve analysis status between runs
            
            # Use COLUMN_CONFIG to determine type conversions
            for col_name, config in self.COLUMN_CONFIG.items():
                if col_name in save_df.columns:
                    column_type = config.column_type
                    if column_type == bool:
                        save_df[col_name] = save_df[col_name].astype(bool).astype(int)
                    elif column_type == int:
                        save_df[col_name] = pd.to_numeric(save_df[col_name], errors='coerce').fillna(0).astype(int)
                    elif column_type == float:
                        save_df[col_name] = pd.to_numeric(save_df[col_name], errors='coerce').fillna(0.0).astype(float)
                    # For str columns, no conversion needed as they're already strings
            
            save_df.to_csv(filepath, index=False)
            logger.info(f"Saved state to: {filepath}")
            return filepath
        return None

    def load_state(self, filepath: str):
        """Load state from a specific CSV file."""
        try:
            if not os.path.exists(filepath):
                logger.warning(f"State file does not exist: {filepath}")
                return
            
            # Load the saved state
            saved_df = pd.read_csv(filepath)
            
            # Ensure all columns exist in the loaded DataFrame
            for col_name in self.df.columns:
                if col_name not in saved_df.columns:
                    saved_df[col_name] = self.get_column_default_value(col_name)
            
            # Robustly convert boolean columns
            for col_name, config in self.COLUMN_CONFIG.items():
                if config.column_type == bool and col_name in saved_df.columns:
                    # Accepts True/False, 1/0, 'True'/'False', NaN
                    def to_bool(val):
                        if pd.isna(val):
                            return False
                        if isinstance(val, bool):
                            return val
                        if isinstance(val, (int, float)):
                            return bool(val)
                        if isinstance(val, str):
                            return val.strip().lower() in ("true", "1", "yes", "y", "t")
                        return False
                    saved_df[col_name] = saved_df[col_name].map(to_bool)
            
            # Update the current DataFrame
            self.df = saved_df
            
            logger.info(f"Loaded state from: {filepath}")
            
        except Exception as e:
            logger.error(f"Error loading state from {filepath}: {e}")
            raise

    # Column management methods for frontend widgets
    def get_column_config(self, column_name: str) -> Dict[str, Any]:
        """Get configuration for a specific column."""
        config = self.COLUMN_CONFIG.get(column_name)
        return config.to_dict() if config else {}

    def get_visible_columns(self, widget_type: str = 'table') -> List[str]:
        """Get list of visible columns for a specific widget type."""
        visible_cols = []
        for col_name, config in self.COLUMN_CONFIG.items():
            if getattr(config, f'{widget_type}_visible', False):
                visible_cols.append(col_name)
        return visible_cols

    def get_column_display_names(self, columns: List[str]) -> List[str]:
        """Get display names for a list of columns."""
        return [
            getattr(self.COLUMN_CONFIG.get(col), 'display_name', col) for col in columns
        ]

    def get_column_width(self, column_name: str) -> Optional[int]:
        """Get width for a specific column."""
        config = self.COLUMN_CONFIG.get(column_name)
        return getattr(config, 'width', None) if config else None

    def is_column_editable(self, column_name: str) -> bool:
        """Check if a column is editable."""
        config = self.COLUMN_CONFIG.get(column_name)
        return getattr(config, 'editable', False) if config else False

    def get_column_widget_type(self, column_name: str) -> Optional[str]:
        """Get widget type for a column."""
        config = self.COLUMN_CONFIG.get(column_name)
        return getattr(config, 'widget_type', None) if config else None

    def is_checkbox_column(self, column_name: str) -> bool:
        """Check if a column is a checkbox column."""
        return self.get_column_widget_type(column_name) == 'checkbox'

    def get_column_backend_field(self, column_name: str) -> Optional[str]:
        """Get the backend field name for a column."""
        config = self.COLUMN_CONFIG.get(column_name)
        return getattr(config, 'backend_field', None) if config else None

    def get_column_type(self, column_name: str) -> type:
        """Get the data type for a specific column."""
        config = self.COLUMN_CONFIG.get(column_name)
        return getattr(config, 'column_type', str) if config else str

    def get_column_tooltip(self, column_name: str) -> Optional[str]:
        """Get the tooltip for a specific column."""
        config = self.COLUMN_CONFIG.get(column_name)
        return getattr(config, 'tooltip', None) if config else None

    def get_all_columns(self) -> List[str]:
        """Get all available columns."""
        return list(self.COLUMN_CONFIG.keys())

    def add_column(self, column_name: str, config: Dict[str, Any] = None):
        """Add a new column to the configuration."""
        if column_name not in self.COLUMN_CONFIG:
            # Create default ColumnConfig with sensible defaults
            default_config = ColumnConfig(
                display_name=column_name.replace('_', ' ').title(),
                width=100,
                editable=False,
                widget_type=None,
                backend_field=column_name,
                tree_visible=False,
                table_visible=False,
                sortable=True,
            )

            # Override with provided config if any
            if config:
                # Convert dict to ColumnConfig by updating the default
                for key, value in config.items():
                    if hasattr(default_config, key):
                        setattr(default_config, key, value)

            self.COLUMN_CONFIG[column_name] = default_config

            # Add to DataFrame if it doesn't exist
            if column_name not in self.df.columns:
                self.df[column_name] = None
                # Auto-save state after adding column
                self._auto_save_state()

    def remove_column(self, column_name: str):
        """Remove a column from the configuration."""
        if column_name in self.COLUMN_CONFIG:
            del self.COLUMN_CONFIG[column_name]

            # Remove from DataFrame if it exists
            if column_name in self.df.columns:
                self.df = self.df.drop(columns=[column_name])
                # Auto-save state after removing column
                self._auto_save_state()

    def get_kym_roi_analysis(self, row_index: int) -> Optional[KymRoiAnalysis]:
        """
        Get or create a KymRoiAnalysis object for a specific row.

        This method implements lazy loading - it only creates the KymRoiAnalysis
        object when first requested, and returns the cached object on subsequent calls.
        
        When load_analysis_csv=True, CSV analysis files are pre-loaded during initialization,
        so this method will return the pre-loaded object without creating a new one.

        Parameters
        ----------
        row_index : int
            The row index in the DataFrame

        Returns
        -------
        Optional[KymRoiAnalysis]
            The KymRoiAnalysis object for the specified row, or None if the row doesn't exist
            or if there's an error loading the file
        """
        if self.df is None or len(self.df) == 0:
            return None

        if row_index < 0 or row_index >= len(self.df):
            logger.error(f"Row index {row_index} is out of bounds (0-{len(self.df)-1})")
            return None

        # Use .at for both reading and writing the cache
        existing_analysis: KymRoiAnalysis = self.df.at[row_index, '_kymRoiAnalysis']
        
        if existing_analysis is not None:
            logger.debug(f"Returning cached analysis for row {row_index}")
            print(existing_analysis)
            return existing_analysis

        # If we get here, the KymRoiAnalysis object wasn't pre-loaded or failed to load
        # This can happen if load_analysis_csv=False or if pre-loading failed for this file
        
        # Get the file path for this row
        relative_path = self.df.at[row_index, 'relative_path']
        tif_path = self.resolve_path(relative_path)

        try:
            # Create the KymRoiAnalysis object
            # Note: KymRoiAnalysis always loads analysis results if available, regardless of load_analysis_csv setting
            # The load_analysis_csv parameter only controls whether we pre-load all KymRoiAnalysis objects during initialization
            logger.info(f'loading KymRoiAnalysis with analysis_only:{True} loadImgData:{False}')
            kym_analysis = KymRoiAnalysis(path=str(tif_path), analysis_only=True, loadImgData=False)
            logger.debug(f"Created KymRoiAnalysis for row {row_index}")

            # Set the KymRoiAnalysis object for this row
            self.df.at[row_index, '_kymRoiAnalysis'] = kym_analysis

            return kym_analysis

        except (FileNotFoundError, PermissionError) as e:
            logger.error(
                f"File access error creating KymRoiAnalysis for {tif_path}: {e}"
            )
            return None
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(
                f"Data format error creating KymRoiAnalysis for {tif_path}: {e}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error creating KymRoiAnalysis for {tif_path}: {e}"
            )
            # Re-raise unexpected errors to avoid masking bugs
            raise

    def load_kym_roi_analysis_image_data(self, row_index: int) -> bool:
        """
        Load image data for a KymRoiAnalysis object that was created without image data.
        
        This method is useful when you need to access image data for visualization
        or analysis that requires the actual image pixels.
        
        Parameters
        ----------
        row_index : int
            The row index in the DataFrame
            
        Returns
        -------
        bool
            True if image data was successfully loaded, False otherwise
        """
        if self.df is None or len(self.df) == 0:
            return False

        if row_index < 0 or row_index >= len(self.df):
            logger.error(f"Row index {row_index} is out of bounds (0-{len(self.df)-1})")
            return False

        # Get the existing KymRoiAnalysis object
        kym_analysis = self.df.at[row_index, '_kymRoiAnalysis']
        if kym_analysis is None:
            logger.warning(f"No KymRoiAnalysis object found for row {row_index}")
            return False

        try:
            # Load image data into the existing KymRoiAnalysis object
            # abb
            # kym_analysis.loadImgData()
            kym_analysis.load_image_data()
            logger.debug(f"Loaded image data for KymRoiAnalysis at row {row_index}")
            return True

        except Exception as e:
            logger.error(f"Failed to load image data for row {row_index}: {e}")
            return False

    def load_kym_roi_analysis_image_data_by_path(self, relative_path: str) -> bool:
        """
        Load image data for a KymRoiAnalysis object by relative path.
        
        Parameters
        ----------
        relative_path : str
            The relative path (e.g., "20250401/SSAN/20250401 SSAN FCCP R2 LS3.tif")
            
        Returns
        -------
        bool
            True if image data was successfully loaded, False otherwise
        """
        if self.df is None or len(self.df) == 0:
            return False

        # Find the row with this relative path
        mask = self.df['relative_path'] == relative_path
        if not mask.any():
            logger.error(f"Relative path not found in DataFrame: {relative_path}")
            return False

        row_index = mask.idxmax()
        return self.load_kym_roi_analysis_image_data(row_index)

    def get_kym_roi_analysis_with_image_data(self, row_index: int) -> Optional[KymRoiAnalysis]:
        """
        Get a KymRoiAnalysis object and ensure image data is loaded.
        
        This method combines get_kym_roi_analysis() and load_kym_roi_analysis_image_data()
        to provide a convenient way to get a fully loaded KymRoiAnalysis object.
        
        Parameters
        ----------
        row_index : int
            The row index in the DataFrame
            
        Returns
        -------
        Optional[KymRoiAnalysis]
            The KymRoiAnalysis object with image data loaded, or None if failed
        """
        # First get the KymRoiAnalysis object (creates it if needed)
        kym_analysis = self.get_kym_roi_analysis(row_index)
        if kym_analysis is None:
            return None

        # Check if image data is already loaded
        if hasattr(kym_analysis, 'imgData') and kym_analysis.imgData is not None:
            logger.debug(f"Image data already loaded for row {row_index}")
            return kym_analysis

        # Load image data if not already loaded
        if self.load_kym_roi_analysis_image_data(row_index):
            return kym_analysis
        else:
            logger.error(f"Failed to load image data for row {row_index}")
            return None

    def get_kym_roi_analysis_with_image_data_by_path(self, relative_path: str) -> Optional[KymRoiAnalysis]:
        """
        Get a KymRoiAnalysis object with image data loaded by relative path.
        
        Parameters
        ----------
        relative_path : str
            The relative path (e.g., "20250401/SSAN/20250401 SSAN FCCP R2 LS3.tif")
            
        Returns
        -------
        Optional[KymRoiAnalysis]
            The KymRoiAnalysis object with image data loaded, or None if failed
        """
        if self.df is None or len(self.df) == 0:
            return None

        # Find the row with this relative path
        mask = self.df['relative_path'] == relative_path
        if not mask.any():
            logger.error(f"Relative path not found in DataFrame: {relative_path}")
            return None

        row_index = mask.idxmax()
        return self.get_kym_roi_analysis_with_image_data(row_index)

    def _find_file_by_path(self, tif_path: str) -> Optional[int]:
        """
        Find a file in the backend DataFrame by path (absolute or relative).
        
        This helper method handles the conversion between absolute and relative paths
        to find the correct row in the backend DataFrame.
        
        Parameters
        ----------
        tif_path : str
            Path to the TIF file (can be absolute or relative)
            
        Returns
        -------
        Optional[int]
            Row index if found, None if not found
        """
        if self.df is None or len(self.df) == 0:
            return None
            
        # Convert input to Path object for cross-platform safety
        input_path = Path(tif_path)
        
        # First, try to find by relative path (if input was relative)
        if not input_path.is_absolute():
            # Store relative paths as POSIX format for cross-platform compatibility
            posix_rel_path = input_path.as_posix()
            mask = self.df['relative_path'] == posix_rel_path
            if mask.any():
                return mask.idxmax()
        
        # If not found or input was absolute, resolve to absolute path and search
        resolved_input_path = self.resolve_path(tif_path)
        mask = self.df['relative_path'].apply(lambda x: self.resolve_path(x) == resolved_input_path)
        if mask.any():
            return mask.idxmax()
            
        return None

    def get_column_default_value(self, column_name: str) -> Any:
        """
        Get the default value for a specific column.
        
        Parameters
        ----------
        column_name : str
            Name of the column
            
        Returns
        -------
        Any
            Default value for the column, or None if column doesn't exist
        """
        config = self.COLUMN_CONFIG.get(column_name)
        return config.default_value if config else None

    def update_analysis(self, tif_path: str) -> bool:
        """
        Update analysis-related columns for a specific TIF file using lazy KymRoiAnalysis loading.
        
        This method finds the file in the backend DataFrame and updates analysis-related
        columns (like numRois) by loading the KymRoiAnalysis object in analysis-only mode.
        
        Parameters
        ----------
        tif_path : str
            Path to the TIF file to update (can be absolute or relative).
            The method will automatically find the file in the backend regardless of path type.
            
        Returns
        -------
        bool
            True if analysis was successfully updated, False otherwise
        """
        try:
            # Find the row index in the backend DataFrame using helper method
            row_index = self._find_file_by_path(tif_path)
            if row_index is None:
                logger.warning(f"File not found in backend: {tif_path}")
                return False
            
            # Get the KymRoiAnalysis object for this file (lazy loading)
            kym_analysis = self.get_kym_roi_analysis(row_index)
            if kym_analysis is None:
                logger.warning(f"Failed to load KymRoiAnalysis for {tif_path}")
                return False
            
            # Update analysis-related columns
            updated_columns = []
            
            # Update numRois if the column exists
            if 'numRois' in self.df.columns:
                try:
                    # Use the proper KymRoiAnalysis API method to get number of ROIs
                    num_rois = kym_analysis.numRoi
                    if num_rois is not None:
                        self.df.at[row_index, 'numRois'] = int(num_rois)
                        updated_columns.append('numRois')
                        logger.debug(f"Updated numRois to {num_rois} for {tif_path}")
                except (AttributeError, ValueError) as e:
                    logger.warning(f"Failed to update numRois for {tif_path}: {e}")
            
            # Note: TifPool updates are handled by on_analysis_saved() method
            # to avoid duplicate refresh calls

            # EXTENDING THIS METHOD:
            # To add new analysis-related columns, follow this pattern:
            # 1. Check if the column exists: if 'ColumnName' in self.df.columns:
            # 2. Get the value from KymRoiAnalysis: value = getattr(kym_analysis, 'attribute_name', None)
            # 3. Update the DataFrame: self.df.at[row_index, 'ColumnName'] = value
            # 4. Track the update: updated_columns.append('ColumnName')
            # 5. Add error handling: except (AttributeError, ValueError) as e: logger.warning(...)
            #
            # Example:
            # if 'PeakCount' in self.df.columns:
            #     try:
            #         peak_count = getattr(kym_analysis, 'peakCount', None)
            #         if peak_count is not None:
            #             self.df.at[row_index, 'PeakCount'] = int(peak_count)
            #             updated_columns.append('PeakCount')
            #             logger.debug(f"Updated PeakCount to {peak_count} for {tif_path}")
            #     except (AttributeError, ValueError) as e:
            #         logger.warning(f"Failed to update PeakCount for {tif_path}: {e}")
            
            if updated_columns:
                logger.info(f"Updated analysis for {tif_path}: {', '.join(updated_columns)}")
                # Auto-save state after updating analysis
                self._auto_save_state()
                return True
            else:
                logger.warning(f"No analysis columns were updated for {tif_path}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update analysis for {tif_path}: {e}")
            return False

    def get_kym_roi_analysis_by_path(
        self, relative_path: str
    ) -> Optional[KymRoiAnalysis]:
        """
        Get or create a KymRoiAnalysis object for a specific relative path.

        Parameters
        ----------
        relative_path : str
            The relative path (e.g., "20250401/SSAN/20250401 SSAN FCCP R2 LS3.tif")

        Returns
        -------
        Optional[KymRoiAnalysis]
            The KymRoiAnalysis object for the specified relative path, or None if not found
        """
        if self.df is None or len(self.df) == 0:
            return None

        # Find the row with this relative path
        mask = self.df['relative_path'] == relative_path
        if not mask.any():
            logger.error(f"Relative path not found in DataFrame: {relative_path}")
            return None

        row_index = mask.idxmax()

        # logger.info(f'found row_index:{row_index} for relative_path:{relative_path}')

        return self.get_kym_roi_analysis(row_index)

    def clear_kym_roi_analysis_cache(self):
        """
        Clear all cached KymRoiAnalysis objects to free memory.

        This is useful when you want to free up memory or when you suspect
        the cached objects might be stale.
        """
        if self.df is not None and '_kymRoiAnalysis' in self.df.columns:
            self.df['_kymRoiAnalysis'] = None
            logger.info("Cleared KymRoiAnalysis cache")

    def get_cached_kym_roi_analysis_count(self) -> int:
        """
        Get the number of currently cached KymRoiAnalysis objects.

        Returns
        -------
        int
            Number of cached KymRoiAnalysis objects
        """
        if self.df is None or '_kymRoiAnalysis' not in self.df.columns:
            return 0

        return self.df['_kymRoiAnalysis'].notna().sum()

    def get_full_path(self, relative_path: str) -> str:
        """
        Get the full path for a relative path.

        Parameters
        ----------
        relative_path : str
            The relative path

        Returns
        -------
        str
            The full absolute path
        """
        return str(self.resolve_path(relative_path))

    def resolve_path(self, path: str) -> Path:
        """
        Resolve a path to an absolute Path object.

        If the path is relative, it will be resolved relative to the backend's root_path.
        If the path is already absolute, it will be normalized.

        Parameters
        ----------
        path : str
            The path to resolve (can be absolute or relative)

        Returns
        -------
        Path
            The resolved absolute Path object
        """
        path_obj = Path(path)
        if not path_obj.is_absolute():
            # If it's a relative path, resolve it relative to root_path
            resolved_path = self.root_path / path_obj
        else:
            resolved_path = path_obj

        # Normalize the path to handle different separators and resolve any relative components
        return resolved_path.resolve()


