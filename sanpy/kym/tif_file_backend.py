import os
import re
from typing import List, Optional, Dict, Any, Union
import pandas as pd

from sanpy.kym.logger import get_logger
from sanpy.kym.tif_info import TifInfo

logger = get_logger(__name__)

class TifFileBackend:
    """Backend class for managing .tif file data and metadata.
    
    Given a root path, loads all .tif files into DataFrame.
    
    Can save as csv file to root_path/tif_file_backend_state.csv
    """
    
    # Define column structure for easy modification
    COLUMNS = {
        'relative_path': str,
        'full_path': str,
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
        'show_file': bool
    }
    
    def __init__(self, root_path: str, exclude_folders: List[str] = None):
        """
        Initialize the backend with a root path and optional folder exclusions.
        
        Parameters
        ----------
        root_path : str
            Root directory to scan for .tif files
        exclude_folders : List[str], optional
            List of folder names to exclude from scanning
        """
        self.root_path = root_path
        self.exclude_folders = exclude_folders or ["sanpy-reports-pdf"]
        
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
                    common_cols = [col for col in loaded_df.columns if col in self.df.columns and col in self.COLUMNS and col != 'full_path']
                    
                    if common_cols:
                        # Create a mapping dataframe with only the columns we want to update
                        update_df = loaded_df[['full_path'] + common_cols].copy()
                        
                        # Step 1: Handle special column types before merging
                        # Ensure 'repeat' column is integer type
                        if 'repeat' in common_cols:
                            update_df['repeat'] = pd.to_numeric(update_df['repeat'], errors='coerce').fillna(0).astype(int)
                        
                        # Step 2: Convert 0/1 to Python booleans for checkbox columns
                        for col in ['show_file']:
                            if col in common_cols:
                                # Convert 0/1 to Python booleans
                                update_df[col] = update_df[col].astype(int).astype(bool)
                        
                        # Step 3: Merge by full_path and update only the specified columns
                        for col in common_cols:
                            # Step 3a: Create a mapping from loaded data
                            mapping_series = update_df.set_index('full_path')[col]
                            
                            # Step 3b: Apply the mapping to update the main dataframe
                            mapped_values = self.df['full_path'].map(mapping_series)
                            
                            # Step 3c: Fill missing values with existing data
                            updated_column = mapped_values.fillna(self.df[col])
                            
                            # Step 3d: Update the main dataframe with proper type conversion
                            if col in ['show_file']:
                                # Ensure Python boolean type (not numpy.bool_)
                                updated_column = updated_column.map(lambda x: bool(x))
                                updated_column = updated_column.astype(object)
                            elif col == 'repeat':
                                updated_column = pd.to_numeric(updated_column, errors='coerce').fillna(0).astype(int)
                            elif col in ['parent_folder', 'grandparent_folder', 'great_grandparent_folder']:
                                # Ensure folder columns are always strings
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
                
                for tif_file in tif_files:
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
                        'full_path': full_path,
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
                        'show_file': True
                    })
                    
        except PermissionError as e:
            logger.error(f"Permission denied accessing {self.root_path}: {e}")
        except Exception as e:
            logger.error(f"Error scanning {self.root_path}: {e}")
        
        # Create DataFrame from collected data
        self.df = pd.DataFrame(file_data)
        
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
            return self.df[self.df['show_file']]['full_path'].tolist()
        
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
            mask = self.df['full_path'] == identifier
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
        """Load state from a CSV file."""
        if os.path.exists(filepath):
            try:
                loaded_df = pd.read_csv(filepath)
                # Convert 0/1 to Python booleans for checkbox columns
                for col in ['show_file']:
                    if col in loaded_df.columns:
                        loaded_df[col] = loaded_df[col].astype(int).astype(bool)
                if len(self.df) > 0 and len(loaded_df) > 0:
                    # Only load columns that exist in both dataframes and are expected, EXCLUDING 'full_path'
                    common_cols = [col for col in loaded_df.columns if col in self.df.columns and col in self.COLUMNS and col != 'full_path']
                    if common_cols:
                        update_df = loaded_df[['full_path'] + common_cols].copy()
                        if 'repeat' in common_cols:
                            update_df['repeat'] = pd.to_numeric(update_df['repeat'], errors='coerce').fillna(0).astype(int)
                        for col in common_cols:
                            mapping_series = update_df.set_index('full_path')[col]
                            mapped_values = self.df['full_path'].map(mapping_series)
                            updated_column = mapped_values.fillna(self.df[col])
                            if col in ['show_file']:
                                # Ensure Python boolean type (not numpy.bool_)
                                updated_column = updated_column.map(lambda x: bool(x))
                                updated_column = updated_column.astype(object)
                            elif col == 'repeat':
                                updated_column = pd.to_numeric(updated_column, errors='coerce').fillna(0).astype(int)
                            elif col in ['parent_folder', 'grandparent_folder', 'great_grandparent_folder']:
                                # Ensure folder columns are always strings
                                updated_column = updated_column.astype(str)
                                # Convert 'nan' strings back to empty strings
                                updated_column = updated_column.replace('nan', '')
                            elif hasattr(updated_column, 'infer_objects') and updated_column.dtype == 'object':
                                updated_column = updated_column.infer_objects(copy=False)
                            self.df[col] = updated_column
                        logger.info(f"Loaded state from: {filepath}")
                    else:
                        logger.warning(f"No matching columns found in saved state file: {filepath}")
            except Exception as e:
                logger.error(f"Error loading state from {filepath}: {e}") 