"""
TifFileBackend - Backend class for managing .tif file data and metadata.

HOW TO ADD NEW COLUMNS:
======================

1. ADD TO COLUMNS DICTIONARY (around line 25):
   Add your column with its data type:
   'your_column': str,  # or int, bool, float, etc.

2. ADD TO COLUMN_CONFIG DICTIONARY (around line 40):
   Add configuration for display and behavior:
   'your_column': ColumnConfig(
       display_name='Your Column',  # What users see
       width=100,                   # Column width (None for auto)
       stretch=False,               # Should column stretch?
       editable=False,              # Can users edit this column?
       widget_type=None,            # 'checkbox', 'dropdown', etc.
       tree_visible=True,           # Show in tree widget?
       table_visible=True,          # Show in table widget?
       sortable=True                # Can users sort by this column?
   )

3. ADD DATA POPULATION (around line 400):
   In the file_data.append() call, add your data:
   'your_column': your_value_or_calculation,

4. ADD TYPE CONVERSION (if needed, around line 280):
   If your column needs special type conversion when loading from CSV:
   if 'your_column' in common_cols:
       update_df['your_column'] = your_conversion_function(update_df['your_column'])

5. ADD TYPE CONVERSION IN MAIN LOOP (if needed, around line 300):
   In the column update loop, add your type conversion:
   elif col == 'your_column':
       updated_column = your_conversion_function(updated_column)

EXAMPLES:
- String column: Just add to COLUMNS and COLUMN_CONFIG
- Integer column: Add type conversion in _load_saved_state
- Boolean column: Add to checkbox conversion list
- Calculated column: Add calculation in _scan_files

SPECIAL COLUMNS:
- _KymRoiAnalysis: Special column that stores KymRoiAnalysis objects in memory during runtime.
  This column is NOT saved to CSV files and is used for lazy loading of analysis objects.
  Use get_kym_roi_analysis(row_index) or get_kym_roi_analysis_by_path(tif_path) to access.

WIDGET COMPATIBILITY:
- Table widget: Automatically shows columns with table_visible=True
- Tree widget: Currently uses hardcoded columns (needs refactoring)
"""

import os
import re
# import random  # Uncomment when adding columns that need random data
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
import pandas as pd

from sanpy.kym.logger import get_logger
from sanpy.kym.tif_info import TifInfo
from sanpy.kym.kymRoiAnalysis import KymRoiAnalysis

logger = get_logger(__name__)

@dataclass
class ColumnConfig:
    """Configuration for a column in the TifFileBackend.
    
    This dataclass provides a type-safe way to configure column behavior
    and appearance across different UI widgets.
    """
    display_name: str
    width: Optional[int] = None
    stretch: bool = False
    editable: bool = False
    widget_type: Optional[str] = None
    backend_field: Optional[str] = None
    tree_visible: bool = False
    table_visible: bool = False
    sortable: bool = True
    
    def __post_init__(self):
        """Auto-set backend_field if not provided."""
        if self.backend_field is None:
            # Convert display_name to snake_case for backend field
            self.backend_field = self.display_name.lower().replace(' ', '_')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return {
            'display_name': self.display_name,
            'width': self.width,
            'stretch': self.stretch,
            'editable': self.editable,
            'widget_type': self.widget_type,
            'backend_field': self.backend_field,
            'tree_visible': self.tree_visible,
            'table_visible': self.table_visible,
            'sortable': self.sortable
        }

class TifFileBackend:
    """Backend class for managing .tif file data and metadata.
    
    Given a root path, loads all .tif files into DataFrame.
    
    Can save as csv file to root_path/tif_file_backend_state.csv
    """
    
    # Define column structure for easy modification
    # IMPORTANT: When adding new columns, you need to:
    # 1. Add the column here with its data type
    # 2. Add column configuration below in COLUMN_CONFIG
    # 3. Add data population in _scan_files() method
    # 4. Add type conversion in _load_saved_state() method if needed
    COLUMNS = {
        'relative_path': str,
        'filename': str,
        'parent_folder': str,
        'grandparent_folder': str,
        'great_grandparent_folder': str,
        'date': str,
        'cell_id': str,
        'region': str,
        'condition': str,
        'repeat': int,
        'error': str,
        'show_file': bool,
        'note': str,  # New editable note column
        '_KymRoiAnalysis': object,  # Special column for storing KymRoiAnalysis objects in memory
        '_KymRoiAnalysis_Loaded': bool,  # Track loading status for UI display
        # '_random_': int  # Example: New random column (commented out)
    }
    
    # Column display configuration for UI widgets
    COLUMN_CONFIG = {
        # Core display columns (always shown)
        'filename': ColumnConfig(
            display_name='Filename',
            width=None,  # Will stretch
            stretch=True,
            editable=False,
            widget_type=None,
            backend_field='filename',
            tree_visible=True,
            table_visible=True,
            sortable=True
        ),
        'date': ColumnConfig(
            display_name='Date',
            width=100,
            stretch=False,
            editable=False,
            widget_type=None,
            backend_field='date',
            tree_visible=True,
            table_visible=True,
            sortable=True
        ),
        'cell_id': ColumnConfig(
            display_name='Cell ID',
            width=80,
            stretch=False,
            editable=False,
            widget_type=None,
            backend_field='cell_id',
            tree_visible=True,
            table_visible=True,
            sortable=True
        ),
        'region': ColumnConfig(
            display_name='Region',
            width=80,
            stretch=False,
            editable=False,
            widget_type=None,
            backend_field='region',
            tree_visible=True,
            table_visible=True,
            sortable=True
        ),
        'condition': ColumnConfig(
            display_name='Condition',
            width=100,
            stretch=False,
            editable=False,
            widget_type=None,
            backend_field='condition',
            tree_visible=True,
            table_visible=True,
            sortable=True
        ),
        'repeat': ColumnConfig(
            display_name='Repeat',
            width=80,
            stretch=False,
            editable=False,
            widget_type=None,
            backend_field='repeat',
            tree_visible=True,
            table_visible=True,
            sortable=True
        ),
        'note': ColumnConfig(
            display_name='Note',
            width=150,
            stretch=False,
            editable=True,  # Make it editable
            widget_type=None,
            backend_field='note',
            tree_visible=False,  # Not in tree by default
            table_visible=True,  # Show in table
            sortable=True
        ),
        'show_file': ColumnConfig(
            display_name='Show',
            width=80,
            stretch=False,
            editable=True,
            widget_type='checkbox',
            backend_field='show_file',
            tree_visible=True,
            table_visible=True,
            sortable=False
        ),
        # '_random_': {
        #     'display_name': 'Random',
        #     'width': 80,
        #     'stretch': False,
        #     'editable': False,
        #     'widget_type': None,
        #     'backend_field': '_random_',
        #     'tree_visible': True,
        #     'table_visible': True,
        #     'sortable': True
        # },
        # Hidden columns (for internal use)
        'relative_path': ColumnConfig(
            display_name='Relative Path',
            width=None,
            stretch=False,
            editable=False,
            widget_type=None,
            backend_field='relative_path',
            tree_visible=False,
            table_visible=False,
            sortable=True
        ),
        'parent_folder': ColumnConfig(
            display_name='Parent Folder',
            width=None,
            stretch=False,
            editable=False,
            widget_type=None,
            backend_field='parent_folder',
            tree_visible=False,
            table_visible=False,
            sortable=True
        ),
        'grandparent_folder': ColumnConfig(
            display_name='Grandparent Folder',
            width=None,
            stretch=False,
            editable=False,
            widget_type=None,
            backend_field='grandparent_folder',
            tree_visible=False,
            table_visible=False,
            sortable=True
        ),
        'great_grandparent_folder': ColumnConfig(
            display_name='Great Grandparent Folder',
            width=None,
            stretch=False,
            editable=False,
            widget_type=None,
            backend_field='great_grandparent_folder',
            tree_visible=False,
            table_visible=False,
            sortable=True
        ),
        'error': ColumnConfig(
            display_name='Error',
            width=80,
            stretch=False,
            editable=False,
            widget_type=None,
            backend_field='error',
            tree_visible=False,
            table_visible=False,
            sortable=True
        ),
        '_KymRoiAnalysis': ColumnConfig(
            display_name='KymRoiAnalysis',
            width=None,
            stretch=False,
            editable=False,
            widget_type=None,
            backend_field='_KymRoiAnalysis',
            tree_visible=False,
            table_visible=False,
            sortable=False
        ),
        '_KymRoiAnalysis_Loaded': ColumnConfig(
            display_name='Kym Loaded',
            width=80,
            stretch=False,
            editable=False,
            widget_type='status_icon',
            backend_field='_KymRoiAnalysis_Loaded',
            tree_visible=False,
            table_visible=True,
            sortable=False
        )
    }
    
    def __init__(self, root_path: str, exclude_folders: List[str] = None, sort_by_grandparent: bool = True):
        """
        Initialize the backend with a root path and optional folder exclusions.
        
        Parameters
        ----------
        root_path : str
            Root directory to scan for .tif files
        exclude_folders : List[str], optional
            List of folder names to exclude from scanning
        sort_by_grandparent : bool, optional
            If True, sort files by grandparent folder (ignoring parent folder).
            If False, sort files by parent folder. Default is True.
        """
        self.root_path = root_path
        self.exclude_folders = exclude_folders or ["sanpy-reports-pdf"]
        self.sort_by_grandparent = sort_by_grandparent
        
        # Initialize DataFrame with proper column structure
        self.df = pd.DataFrame(columns=list(self.COLUMNS.keys()))
        
        if not os.path.exists(root_path):
            logger.error(f"Root path does not exist: {root_path}")
            return
            
        self._scan_files()
        self._load_saved_state()
    
    def _should_exclude_path(self, path: str) -> bool:
        """Check if path contains any excluded folders."""
        return any(excluded in path for excluded in self.exclude_folders)
    
    def _get_state_filepath(self) -> str:
        """Get the filepath for saving/loading state."""
        return os.path.join(self.root_path, "tif_file_backend_state.csv")
    
    def _load_saved_state(self):
        """Load saved state from CSV file if it exists."""
        state_filepath = self._get_state_filepath()
        if os.path.exists(state_filepath):
            try:
                loaded_df = pd.read_csv(state_filepath)
                
                if len(self.df) > 0 and len(loaded_df) > 0:
                    # Only load columns that exist in both dataframes and are expected, EXCLUDING 'full_path'
                    common_cols = [col for col in loaded_df.columns if col in self.df.columns and col in self.COLUMNS]
                    
                    # Ensure relative_path is available for mapping
                    if 'relative_path' not in loaded_df.columns:
                        logger.error(f"relative_path column missing from saved state file: {state_filepath}")
                        return
                    
                    if common_cols:
                        # Create a mapping dataframe with only the columns we want to update
                        # Include relative_path for mapping, but don't process it as a regular column
                        update_cols = ['relative_path'] + [col for col in common_cols if col != 'relative_path']
                        update_df = loaded_df[update_cols].copy()
                        
                        # Step 1: Handle special column types before merging
                        # Ensure 'repeat' column is integer type
                        if 'repeat' in common_cols:
                            update_df['repeat'] = pd.to_numeric(update_df['repeat'], errors='coerce').fillna(0).astype(int)
                        
                        # Ensure '_random_' column is integer type
                        # if '_random_' in common_cols:
                        #     update_df['_random_'] = pd.to_numeric(update_df['_random_'], errors='coerce').fillna(0).astype(int)
                        
                        # Step 2: Convert 0/1 to Python booleans for checkbox columns
                        for col in ['show_file']:
                            if col in common_cols:
                                # Convert 0/1 to Python booleans
                                update_df[col] = update_df[col].astype(int).astype(bool)
                        
                        # Step 3: Merge by relative_path and update only the specified columns
                        for col in common_cols:
                            if col == 'relative_path':
                                continue  # Never update or map the index column itself
                            # Step 3a: Create a mapping from loaded data
                            mapping_series = update_df.set_index('relative_path')[col]
                            
                            # Step 3b: Apply the mapping to update the main dataframe
                            mapped_values = self.df['relative_path'].map(mapping_series)
                            
                            # Step 3c: Fill missing values with existing data
                            updated_column = mapped_values.fillna(self.df[col])
                            
                            # Step 3d: Update the main dataframe with proper type conversion
                            if col in ['show_file']:
                                # Ensure Python boolean type (not numpy.bool_)
                                updated_column = updated_column.map(lambda x: bool(x))
                                updated_column = updated_column.astype(object)
                            elif col == 'repeat':
                                updated_column = pd.to_numeric(updated_column, errors='coerce').fillna(0).astype(int)
                            # elif col == '_random_':
                            #     updated_column = pd.to_numeric(updated_column, errors='coerce').fillna(0).astype(int)
                            elif col in ['parent_folder', 'grandparent_folder', 'great_grandparent_folder']:
                                # Ensure folder columns are always strings
                                updated_column = updated_column.astype(str)
                                # Convert 'nan' strings back to empty strings
                                updated_column = updated_column.replace('nan', '')
                            elif col == 'note':
                                # Ensure note column is always string and handle NaN values
                                updated_column = updated_column.astype(str)
                                # Convert 'nan' strings back to empty strings
                                updated_column = updated_column.replace('nan', '')
                            elif hasattr(updated_column, 'infer_objects') and updated_column.dtype == 'object':
                                updated_column = updated_column.infer_objects(copy=False)
                            self.df[col] = updated_column
                        
                        logger.info(f"Loaded state from: {state_filepath}")
                    else:
                        logger.warning(f"No matching columns found in saved state file: {state_filepath}")
            except Exception as e:
                logger.error(f"Error loading state from {state_filepath}: {e}")
    
    def _scan_files(self):
        """Scan for .tif files and populate the dataframe."""
        logger.info(f"Scanning for .tif files in: {self.root_path}")
        
        file_data = []
        
        try:
            for root, dirs, files in os.walk(self.root_path):
                # Skip if this path should be excluded
                if self._should_exclude_path(root):
                    continue
                
                # Filter for .tif files and sort them
                tif_files = sorted([f for f in files if f.lower().endswith('.tif')])
                
                # logger.debug('')
                # print(f"Found {len(tif_files)} .tif files in {root}: {tif_files}")

                # logger.warning(f'root:{root}')

                for _idx, tif_file in enumerate(tif_files):

                    # print(f'  _idx:{_idx} of {len(tif_files)} tif_file:{tif_file}')

                    full_path = os.path.join(root, tif_file)
                    
                    # Calculate relative path
                    try:
                        relative_path = os.path.relpath(full_path, self.root_path)
                    except ValueError:
                        # Handle case where paths are on different drives
                        relative_path = full_path
                    
                    # Extract folder hierarchy
                    path_parts = relative_path.split(os.sep)
                    
                    if len(path_parts) >= 4:
                        # We have enough levels for the full hierarchy
                        parent_folder = path_parts[-2]  # Folder containing the .tif file
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
                    
                    # Parse filename with TifInfo
                    try:
                        tif_info = TifInfo.from_filename(tif_file)
                        date = tif_info.date
                        cell_id = tif_info.cellid
                        region = tif_info.region
                        condition = tif_info.condition
                        repeat = tif_info.repeat
                        error = tif_info.error
                    except Exception as e:
                        # If TifInfo parsing fails, use default values and log the error
                        logger.warning(f"Failed to parse filename '{tif_file}': {e}")
                        date = ""
                        cell_id = ""
                        region = ""
                        condition = "Unknown"
                        repeat = 0
                        error = str(e)
                    
                    file_data.append({
                        'relative_path': relative_path,
                        'filename': tif_file,
                        'parent_folder': parent_folder,
                        'grandparent_folder': grandparent_folder,
                        'great_grandparent_folder': great_grandparent_folder,
                        'date': date,
                        'cell_id': cell_id,
                        'region': region,
                        'condition': condition,
                        'repeat': repeat,
                        'error': error,
                        'show_file': True,
                        'note': '',  # Initialize note to empty string
                        '_KymRoiAnalysis': None,  # Initialize to None, will be created on demand
                        '_KymRoiAnalysis_Loaded': False,  # Track loading status for UI display
                        # '_random_': random.randint(0, 100)  # Example: Generate random value 0-100
                    })
        except PermissionError as e:
            logger.error(f"Permission denied accessing {self.root_path}: {e}")
        except Exception as e:
            logger.error(f"Error scanning {self.root_path}: {e}")
        
        # Create DataFrame from collected data
        self.df = pd.DataFrame(file_data)
        
        # Sort by grandparent_folder first, then by filename
        # This groups all files in the same grandparent folder together
        if len(self.df) > 0:
            if self.sort_by_grandparent:
                self.df = self.df.sort_values(['great_grandparent_folder', 'grandparent_folder', 'filename'])
            else:
                self.df = self.df.sort_values(['parent_folder', 'filename'])
        
        if len(self.df) > 0:
            logger.info(f"Found {len(self.df)} .tif files")
        else:
            logger.warning("No .tif files found")
    
    def get(self, item_type: str, **kwargs) -> Union[List[str], Dict[str, int], List[str], int]:
        """
        Get data from the backend.
        
        Parameters
        ----------
        item_type : str
            Type of data to retrieve. Valid options:
            - 'files': Get checked file paths
            - 'file_count': Get total number of files
            - 'condition_counts': Get counts by condition
            - 'repeat_counts': Get counts by repeat number
            - 'unique_conditions': Get list of unique conditions
            - 'unique_repeats': Get list of unique repeat numbers
            - 'filter_by_condition': Filter by condition (requires condition parameter)
            - 'filter_by_repeat': Filter by repeat (requires repeat parameter)
        
        Returns
        -------
        Union[List[str], Dict[str, int], List[str], int, pd.DataFrame]
            The requested data
        """
        if self.df is None or len(self.df) == 0:
            return [] if item_type in ['files', 'unique_conditions', 'unique_repeats'] else {}
        
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
            raise ValueError(f"Invalid item_type: {item_type}. Valid options: ['files', 'file_count', 'condition_counts', 'repeat_counts', 'unique_conditions', 'unique_repeats', 'filter_by_condition', 'filter_by_repeat']")
    
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
            # Convert full path to relative path for matching
            if os.path.isabs(identifier):
                # If it's an absolute path, convert to relative path
                try:
                    relative_path = os.path.relpath(identifier, self.root_path)
                except ValueError:
                    # Handle case where paths are on different drives
                    relative_path = identifier
            else:
                relative_path = identifier
            
            mask = self.df['relative_path'] == relative_path
            if mask.any():
                # Ensure we're setting a Python bool, not numpy.bool_
                self.df.loc[mask, 'show_file'] = bool(checked)
                # Force the entire column to be native Python bool
                self.df['show_file'] = self.df['show_file'].map(lambda x: bool(x)).astype(object)
        else:
            raise ValueError(f"Invalid item_type: {item_type}. Only 'file' is supported.")
    
    def refresh(self):
        """Refresh the data by re-scanning the files."""
        logger.info("Refreshing file data")
        self._scan_files()
    
    def save_state(self, filepath: str = None):
        """Save the current dataframe state to a CSV file."""
        if len(self.df) > 0:
            if filepath is None:
                filepath = self._get_state_filepath()
            
            # Create a copy for saving to avoid modifying the original
            save_df = self.df.copy()
            
            # Remove the _KymRoiAnalysis column before saving (it contains objects that can't be serialized)
            if '_KymRoiAnalysis' in save_df.columns:
                save_df = save_df.drop(columns=['_KymRoiAnalysis'])
            
            # Remove the _KymRoiAnalysis_Loaded column before saving (it's runtime-only)
            if '_KymRoiAnalysis_Loaded' in save_df.columns:
                save_df = save_df.drop(columns=['_KymRoiAnalysis_Loaded'])
            
            # Convert boolean columns to 0/1 for reliable CSV storage
            for col in ['show_file']:
                if col in save_df.columns:
                    save_df[col] = save_df[col].astype(bool).astype(int)  # True->1, False->0
            
            # Ensure repeat column is integer
            if 'repeat' in save_df.columns:
                save_df['repeat'] = pd.to_numeric(save_df['repeat'], errors='coerce').fillna(0).astype(int)
            
            save_df.to_csv(filepath, index=False)
            logger.info(f"Saved state to: {filepath}")
            return filepath
        return None
    
    def load_state(self, filepath: str):
        """Load state from a specific CSV file."""
        # Implementation for loading from specific file
        pass
    
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
        return [getattr(self.COLUMN_CONFIG.get(col), 'display_name', col) for col in columns]
    
    def get_column_width(self, column_name: str) -> Optional[int]:
        """Get width for a specific column."""
        config = self.COLUMN_CONFIG.get(column_name)
        return getattr(config, 'width', None) if config else None
    
    def is_column_stretch(self, column_name: str) -> bool:
        """Check if a column should stretch."""
        config = self.COLUMN_CONFIG.get(column_name)
        return getattr(config, 'stretch', False) if config else False
    
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
                stretch=False,
                editable=False,
                widget_type=None,
                backend_field=column_name,
                tree_visible=False,
                table_visible=False,
                sortable=True
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
    
    def remove_column(self, column_name: str):
        """Remove a column from the configuration."""
        if column_name in self.COLUMN_CONFIG:
            del self.COLUMN_CONFIG[column_name]
            
            # Remove from DataFrame if it exists
            if column_name in self.df.columns:
                self.df = self.df.drop(columns=[column_name])
    
    def get_kym_roi_analysis(self, row_index: int) -> Optional[KymRoiAnalysis]:
        """
        Get or create a KymRoiAnalysis object for a specific row.
        
        This method implements lazy loading - it only creates the KymRoiAnalysis
        object when first requested, and returns the cached object on subsequent calls.
        
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
        
        # Check if we already have a KymRoiAnalysis object for this row
        existing_analysis = self.df.iloc[row_index]['_KymRoiAnalysis']
        if existing_analysis is not None:
            return existing_analysis
        
        # Get the file path for this row
        relative_path = self.df.iloc[row_index]['relative_path']
        tif_path = self.resolve_path(relative_path)
        
        # logger.info(f'relative_path:{relative_path}')
        # logger.info(f'tif_path:{tif_path}')
        
        try:
            # Create the KymRoiAnalysis object
            logger.info(f"=== Loading KymRoiAnalysis for: {relative_path}")
            kym_analysis = KymRoiAnalysis(path=tif_path)
            
            # Set the KymRoiAnalysis object for this row
            
            # this is my solution
            self.df.at[row_index, '_KymRoiAnalysis'] = kym_analysis
            self.df.at[row_index, '_KymRoiAnalysis_Loaded'] = True
            
            # this was Cursor solutuon which trigger an error "object of type 'KymRoiAnalysis' has no len()"
            # Store it in the DataFrame
            # self.df.iloc[row_index, self.df.columns.get_loc('_KymRoiAnalysis')] = kym_analysis
            
            # Update loading status
            # self.df.iloc[row_index, self.df.columns.get_loc('_KymRoiAnalysis_Loaded')] = True
            
            return kym_analysis
            
        except Exception as e:
            # object of type 'KymRoiAnalysis' has no len()
            logger.error(f"Error creating KymRoiAnalysis for {tif_path}: {e}")
            return None
    
    def get_kym_roi_analysis_by_path(self, relative_path: str) -> Optional[KymRoiAnalysis]:
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
        return self.get_kym_roi_analysis(row_index)
    
    def clear_kym_roi_analysis_cache(self):
        """
        Clear all cached KymRoiAnalysis objects to free memory.
        
        This is useful when you want to free up memory or when you suspect
        the cached objects might be stale.
        """
        if self.df is not None and '_KymRoiAnalysis' in self.df.columns:
            self.df['_KymRoiAnalysis'] = None
            if '_KymRoiAnalysis_Loaded' in self.df.columns:
                self.df['_KymRoiAnalysis_Loaded'] = False
            logger.info("Cleared KymRoiAnalysis cache")
    
    def get_cached_kym_roi_analysis_count(self) -> int:
        """
        Get the number of currently cached KymRoiAnalysis objects.
        
        Returns
        -------
        int
            Number of cached KymRoiAnalysis objects
        """
        if self.df is None or '_KymRoiAnalysis' not in self.df.columns:
            return 0
        
        return self.df['_KymRoiAnalysis'].notna().sum()
    
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
        return self.resolve_path(relative_path)
    
    def resolve_path(self, path: str) -> str:
        """
        Resolve a path to an absolute path.
        
        If the path is relative, it will be resolved relative to the backend's root_path.
        If the path is already absolute, it will be normalized.
        
        Parameters
        ----------
        path : str
            The path to resolve (can be absolute or relative)
            
        Returns
        -------
        str
            The resolved absolute path
        """
        if not os.path.isabs(path):
            # If it's a relative path, resolve it relative to root_path
            resolved_path = os.path.join(self.root_path, path)
        else:
            resolved_path = path
        
        return resolved_path