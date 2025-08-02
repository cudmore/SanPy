"""
TiffPool - Backend class for pooling analysis results from multiple KymRoiAnalysis files.

This class maintains a master DataFrame that summarizes/pools the analysis of all .tif files
analyzed by KymRoiAnalysis. Each KymRoiAnalysis.saveAnalysis() saves CSV files into
sanpy-kym-roi-analysis/<csv_file.csv> where <csv_file.csv> is <base_tif>-ch0-roiPeaks.csv.

TiffPool appends the CSV for each .tif into its own 'master df' and provides APIs to:
- Update rows in master df with new analysis results
- Append rows if they don't exist
- Load existing pooled data
- Save pooled data
- Create mean statistics grouped by (Cell ID, Condition, ROI Label)
"""

import os
import json
import sys
import pandas as pd
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from sanpy.sanpyLogger import get_logger

from sanpy.kym.tif_file_backend import TifFileBackend
from sanpy.kym.kymRoi import PeakDetectionTypes
import numpy as np

logger = get_logger(__name__)

class TiffPool:
    """
    TiffPool pools analysis results from multiple KymRoiAnalysis objects, providing a unified interface for statistics and filtering.

    Grouping columns and metadata columns are user-specified via the constructor:
        - group_columns: columns to group by when aggregating the mean DataFrame
        - metadata_columns: columns to carry along for context in the mean DataFrame

    All grouping and aggregation logic uses these attributes, making TiffPool flexible for different experimental designs.
    """
    def __init__(self, tif_file_backend: TifFileBackend, group_columns=None, metadata_columns=None):
        """
        Initialize TiffPool.

        Args:
            tif_file_backend (TifFileBackend): Backend for loading KymRoiAnalysis data.
            group_columns (list[str], optional): Columns to group by for mean statistics. Defaults to ['Cell ID', 'Condition', 'ROI Label', 'Channel'].
            metadata_columns (list[str], optional): Columns to carry along for context. Defaults to ['Region', 'Date', 'Repeat', 'Analysis Type', 'Polarity'].
        """
        self.tif_file_backend = tif_file_backend
        self.root_path = tif_file_backend.root_path
        self.master_df = pd.DataFrame()
        self.dfMean = pd.DataFrame()  # New attribute for mean statistics
        self.dfErrors = pd.DataFrame(columns=['Cell ID', 'Condition', 'ROI Count', 'Error Message'])  # New attribute for error tracking
        
        # User-specified or default grouping columns
        self._group_columns = group_columns or ['Cell ID',
                                                'Condition',
                                                'ROI Label',
                                                'Repeat',
                                                'Channel']
        # User-specified or default metadata columns
        self._metadata_columns = metadata_columns or ['Region',
                                                      'Date',
                                                      'Repeat',
                                                      'Analysis Type',
                                                      'Polarity']
        
        # Define numeric columns to calculate statistics for
        # These are the main peak analysis metrics from KymRoiAnalysis
        self._numeric_columns = [
            'Peak (s)',
            'Peak Int',
            'Peak Height',
            'Peak Inst Interval (s)',
            'Peak Inst Freq (Hz)',
            'Onset (s)',
            'Onset Int',
            'Onset 10 (s)',
            'Onset 10 Int',
            'Decay (s)',
            'Decay Int',
            'Decay 10 (s)',
            'Decay 10 Int',
            'HW Left (s)',
            'HW Right (s)',
            'HW Left Int',
            'HW Right Int',
            'Rise Time (ms)',
            'Decay Time (ms)',
            '10-90 Rise Time (ms)',
            '10-90 Decay Time (ms)',
            'FW (ms)',
            'FW 10 (ms)',
            'Area Under Peak',
            'fit_m',
            'fit_tau',
            'fit_b',
            'fit_r2',
            'fit_m1',
            'fit_tau1',
            'fit_m2',
            'fit_tau2',
            'fit_r22',
            'Onset 90 (s)',
            'Onset 90 Int',
            'Decay 90 (s)',
            'Decay 90 Int'
        ]

        self._headerDict = {
            'version': 0.1,
        }
        # Try to load existing pooled data
        self.load_pooled_data()

    def _find_file_by_path(self, tif_path: str) -> Optional[int]:
        """
        Find a file in the backend DataFrame by path (absolute or relative).
        
        This helper method delegates to the backend's path finding logic.
        
        Parameters
        ----------
        tif_path : str
            Path to the TIF file (can be absolute or relative)
            
        Returns
        -------
        Optional[int]
            Row index if found, None if not found
        """
        return self.tif_file_backend._find_file_by_path(tif_path)

    def _get_pooled_data_filepath(self) -> str:
        """Get the filepath for saving/loading pooled data in the same folder as TifFileBackend."""
        return str(Path(self.root_path) / "tif_pool_main.csv")

    def _get_mean_data_filepath(self) -> str:
        """Get the filepath for saving/loading mean data in the same folder as TifFileBackend."""
        return str(Path(self.root_path) / "tif_pool_mean.csv")



    def load_pooled_data(self):
        """Load pooled data from CSV file if it exists."""
        filepath = self._get_pooled_data_filepath()
        if os.path.exists(filepath):
            # self.master_df = pd.read_csv(filepath)
            with open(filepath, 'r') as f:
                # Read the first line as JSON
                _loadedHeaderDict = json.loads(f.readline())
                # Read the remaining lines as a DataFrame
                loaded_df = pd.read_csv(f)
            # logger.info(f"Loaded pooled data from: {filepath} ({len(self.master_df)} rows)")
            if _loadedHeaderDict['version'] != self._headerDict['version']:
                logger.error(f"Version mismatch in saved state file: {filepath}")
                # return
            self._headerDict = _loadedHeaderDict
            self.master_df = loaded_df
        else:
            logger.debug(f"No existing pooled data found at: {filepath}")
            self.master_df = pd.DataFrame()
        
        # Load mean data if it exists
        mean_filepath = self._get_mean_data_filepath()
        if os.path.exists(mean_filepath):
            # self.dfMean = pd.read_csv(mean_filepath)
            with open(mean_filepath, 'r') as f:
                # Read the first line as JSON
                _loadedHeaderDict = json.loads(f.readline())
                # Read the remaining lines as a DataFrame
                loaded_df = pd.read_csv(f)
            # logger.info(f"Loaded mean data from: {mean_filepath} ({len(self.dfMean)} rows)")
            if _loadedHeaderDict['version'] != self._headerDict['version']:
                logger.error(f"Version mismatch in saved mean data file: {mean_filepath}")
                # return
            self.dfMean = loaded_df
        else:
            logger.debug(f"No existing mean data found at: {mean_filepath}")
            self.dfMean = pd.DataFrame()
        
        # Cast ROI Label columns to string to ensure consistency
        if len(self.master_df) > 0 and 'ROI Label' in self.master_df.columns:
            self.master_df['ROI Label'] = self.master_df['ROI Label'].astype(str)
            logger.info(f"Cast ROI Label column to string in master_df: {len(self.master_df)} rows")
            
        if len(self.dfMean) > 0 and 'ROI Label' in self.dfMean.columns:
            self.dfMean['ROI Label'] = self.dfMean['ROI Label'].astype(str)
            logger.info(f"Cast ROI Label column to string in dfMean: {len(self.dfMean)} rows")
        
        # Initialize errors DataFrame (no file loading - runtime only)
        self.dfErrors = pd.DataFrame(columns=['Cell ID', 'Condition', 'ROI Count', 'Error Message'])

    def _auto_save_pooled_data(self):
        """Auto-save pooled data to CSV file whenever the master DataFrame is modified."""
        # Call save_pooled_data with default parameters but use info logging
        if len(self.master_df) > 0:
            result = self.save_pooled_data()
            # Override the debug logging with info logging for auto-save
            if result:
                filepath = self._get_pooled_data_filepath()
                logger.info(f"Auto-saved pooled data to: {filepath} ({len(self.master_df)} rows)")
            return result
        else:
            logger.warning("No pooled data to auto-save (master_df is empty)")
            return None

    def _auto_save_mean_data(self):
        """Auto-save mean data to CSV file whenever the mean DataFrame is modified."""
        # Call save_mean_data with default parameters but use info logging
        if len(self.dfMean) > 0:
            result = self.save_mean_data()
            # Override the debug logging with info logging for auto-save
            if result:
                filepath = self._get_mean_data_filepath()
                logger.info(f"Auto-saved mean data to: {filepath} ({len(self.dfMean)} rows)")
            return result
        else:
            logger.warning("No mean data to auto-save (dfMean is empty)")
            return None

    def save_mean_data(self):
        """Save mean data to CSV file in the loaded folder."""
        if len(self.dfMean) > 0:
            filepath = self._get_mean_data_filepath()
            try:
                # self.dfMean.to_csv(filepath, index=False)
                with open(filepath,'w') as f:
                    # save self._headerDict as json
                    f.write(json.dumps(self._headerDict) + '\n')
                    self.dfMean.to_csv(f, index=False)
                logger.debug(f"Saved mean data to: {filepath} ({len(self.dfMean)} rows)")
                return filepath
            except Exception as e:
                logger.error(f"Failed to save mean data to {filepath}: {e}")
                return None
        else:
            logger.debug("No mean data to save (dfMean is empty)")
            return None

    def create_df_mean(self, force_recalculate: bool = False) -> pd.DataFrame:
        """
        Create the mean DataFrame by grouping master_df by the user-specified group_columns.
        Aggregates numeric columns and attaches metadata columns for each group.

        Args:
            force_recalculate (bool): If True, force recalculation even if dfMean exists.
        Returns:
            pd.DataFrame: Aggregated mean DataFrame.
        """
        if len(self.master_df) == 0:
            logger.warning("Cannot create dfMean: master_df is empty")
            self.dfMean = pd.DataFrame()
            return self.dfMean
        
        if len(self.dfMean) > 0 and not force_recalculate:
            # logger.info(f"dfMean already exists with {len(self.dfMean)} rows. Use force_recalculate=True to recalculate.")
            return self.dfMean
        
        # logger.info("Creating dfMean from master_df...")
        
        # Check if required columns exist
        missing_columns = [col for col in self._group_columns if col not in self.master_df.columns]
        if missing_columns:
            logger.error(f"Cannot create dfMean: missing required columns: {missing_columns}")
            self.dfMean = pd.DataFrame()
            return self.dfMean
        
        # Filter to only include columns that actually exist in master_df
        available_numeric_columns = [col for col in self._numeric_columns if col in self.master_df.columns]
        
        if not available_numeric_columns:
            logger.warning("No numeric columns found for statistics calculation")
            # Create basic grouping with just counts using NaN-aware function
            grouped = self.master_df.groupby(self._group_columns).agg({
                'Peak Number': lambda x: x.count()  # Count non-NaN values
            }).reset_index()
            grouped = grouped.rename(columns={'Peak Number': 'Number of Peaks'})
            # Add Area Under Peak (Sum) as NaN (not available)
            grouped['Area Under Peak (Sum)'] = np.nan
            # Ensure Number of Peaks is integer type
            grouped['Number of Peaks'] = grouped['Number of Peaks'].astype('Int64')
            self.dfMean = grouped
        else:
            # logger.info(f"Calculating statistics for {len(available_numeric_columns)} numeric columns")
            
            # Create aggregation dictionary - pandas functions are NaN-aware by default
            agg_dict = {}
            for col in available_numeric_columns:
                agg_dict[col] = ['count', 'mean', 'std', 'sem', 'median', 'min', 'max']
                if col == 'Area Under Peak':
                    agg_dict[col].append('sum')
            
            # Group and aggregate
            grouped = self.master_df.groupby(self._group_columns).agg(agg_dict).reset_index()
            
            # Flatten column names
            grouped.columns = [f"{col[0]}_{col[1]}" if col[1] else col[0] for col in grouped.columns]
            
            # Rename count columns to be more descriptive
            for col in available_numeric_columns:
                count_col = f"{col}_count"
                if count_col in grouped.columns:
                    # Use the first count column as our main count (they should all be the same)
                    if col == available_numeric_columns[0]:
                        grouped = grouped.rename(columns={count_col: 'Number of Peaks'})
                    else:
                        grouped = grouped.drop(columns=[count_col])
            
            # rename _mean column, just drop _mean
            for col in available_numeric_columns:
                mean_col = f"{col}_mean"
                # logger.info(f'mean_col:{mean_col}')
                if mean_col in grouped.columns:
                    grouped = grouped.rename(columns={mean_col: col})

            # Rename Area Under Peak_sum to Area Under Peak (Sum)
            if 'Area Under Peak_sum' in grouped.columns:
                grouped = grouped.rename(columns={'Area Under Peak_sum': 'Area Under Peak (Sum)'})
            
            # Calculate coefficient of variation (CV) for key metrics with NaN handling
            cv_columns = ['Peak Height', 'Peak Inst Interval (s)', 'Peak Inst Freq (Hz)', 
                         'Rise Time (ms)', 'Decay Time (ms)', 'Area Under Peak']
            
            for col in cv_columns:
                mean_col = f"{col}_mean"
                std_col = f"{col}_std"
                if mean_col in grouped.columns and std_col in grouped.columns:
                    # CV = (std / mean) * 100, handle division by zero and NaN
                    mean_values = grouped[mean_col]
                    std_values = grouped[std_col]
                    # Only calculate CV where mean is not zero and not NaN
                    cv_values = pd.Series(index=grouped.index, dtype=float)
                    valid_mask = (mean_values != 0) & (mean_values.notna()) & (std_values.notna())
                    cv_values[valid_mask] = (std_values[valid_mask] / mean_values[valid_mask]) * 100
                    grouped[f"{col}_cv"] = cv_values
            
            # Add metadata columns that should be consistent within groups
            metadata_data = {}
            for col in self._metadata_columns:
                if col in self.master_df.columns:
                    # Take the first value from each group (they should be consistent)
                    metadata_data[col] = self.master_df.groupby(self._group_columns)[col].first().values
            
            # Add Tif Rel Path as metadata (should be consistent within groups)
            if 'Tif Rel Path' in self.master_df.columns:
                metadata_data['Tif Rel Path'] = self.master_df.groupby(self._group_columns)['Tif Rel Path'].first().values
            
            # Add metadata columns to the grouped DataFrame
            for col, values in metadata_data.items():
                grouped[col] = values
            
            # Reorder columns to put metadata columns first, then grouping columns, then statistics
            desired_column_order = []
            
            # 1. Add metadata columns first (if they exist)
            for col in self._metadata_columns:
                if col in grouped.columns:
                    desired_column_order.append(col)
            
            # 2. Add grouping columns
            desired_column_order.extend(self._group_columns)
            
            # 3. Add Number of Peaks
            desired_column_order.append('Number of Peaks')
            
            # 4. Add all other columns (statistics and CV columns)
            existing_columns = set(grouped.columns)
            for col in desired_column_order:
                if col in existing_columns:
                    existing_columns.remove(col)
            
            # Add remaining columns in their current order
            remaining_columns = [col for col in grouped.columns if col in existing_columns]
            desired_column_order.extend(remaining_columns)
            
            # Reorder the DataFrame
            grouped = grouped[desired_column_order]

            # Remove duplicate columns (keep first occurrence)
            grouped = grouped.loc[:, ~grouped.columns.duplicated()]
            
            # Ensure integer columns stay as integers (handle NaN values properly)
            int_columns = ['Number of Peaks', 'Channel']
            for col in int_columns:
                if col in grouped.columns:
                    # Use Int64 dtype which can handle NaN values while staying as integer type
                    grouped[col] = grouped[col].astype('Int64')
            
            # Handle Date column - ensure it's always a string, never float or datetime
            if 'Date' in grouped.columns:
                # Convert to string and remove any decimal points that pandas might have added
                grouped['Date'] = grouped['Date'].astype(str).str.replace('.0', '', regex=False)
            
            self.dfMean = grouped
        
        # Add boolean columns for cell and ROI filtering (needed for KymTreeWidget)
        self._add_filter_columns()
        
        # Add 'Condition Repeat' column for plotting (combines Condition and Repeat)
        if 'Condition' in self.dfMean.columns and 'Repeat' in self.dfMean.columns:
            self.dfMean['Condition Repeat'] = (
                self.dfMean['Condition'].fillna('')
                + ' '
                + self.dfMean['Repeat'].astype(str).fillna('')
            ).str.strip()
            self.dfMean['Condition Repeat'] = self.dfMean['Condition Repeat'].astype('category')
            logger.debug("20250731 Added 'Condition Repeat' column to dfMean")
        
        # Auto-save the mean data
        self._auto_save_mean_data()
        
        # logger.info(f"Created dfMean with {len(self.dfMean)} rows (one per Cell ID/Condition/ROI Label group)")
        return self.dfMean

    def _add_filter_columns(self):
        """
        Add boolean filter columns (show_cell, show_roi) to dfMean for GUI filtering.
        Ensures these columns exist and are boolean True for all rows (no NaN).
        """
        if len(self.dfMean) == 0:
            return
        
        # Always ensure show_roi column exists and is boolean True
        if 'show_roi' not in self.dfMean.columns:
            self.dfMean['show_roi'] = True
            logger.debug("Added 'show_roi' column to dfMean")
        else:
            # Ensure existing column is boolean and has no NaN values
            self.dfMean['show_roi'] = self.dfMean['show_roi'].fillna(True).astype(bool)
            logger.debug("Ensured 'show_roi' column is boolean with no NaN values")
        
        # Always ensure show_cell column exists and is boolean True
        if 'show_cell' not in self.dfMean.columns:
            self.dfMean['show_cell'] = True
            logger.debug("Added 'show_cell' column to dfMean")
        else:
            # Ensure existing column is boolean and has no NaN values
            self.dfMean['show_cell'] = self.dfMean['show_cell'].fillna(True).astype(bool)
            logger.debug("Ensured 'show_cell' column is boolean with no NaN values")

    def detect_roi_count_mismatches(self, force_recalculate: bool = False) -> pd.DataFrame:
        """
        Detect errors where a Cell ID has different numbers of ROIs between conditions.
        
        This method analyzes the dfMean DataFrame to find cases where the same Cell ID
        has different numbers of ROIs across different conditions.
        
        Parameters
        ----------
        force_recalculate : bool, optional
            If True, recalculate even if dfErrors already exists. Default is False.
            
        Returns
        -------
        pd.DataFrame
            DataFrame containing detected errors with columns:
            - Error Type: Type of error (e.g., "ROI Count Mismatch")
            - Cell ID: The cell ID with the error
            - Error Message: Detailed error description
            - Conditions: List of conditions involved
            - ROI Counts: Dictionary of condition -> ROI count
            - Timestamp: When the error was detected
        """
        if len(self.dfMean) == 0:
            logger.warning("Cannot detect ROI count mismatches: dfMean is empty")
            self.dfErrors = pd.DataFrame()
            return self.dfErrors
        
        if len(self.dfErrors) > 0 and not force_recalculate:
            logger.debug(f"dfErrors already exists with {len(self.dfErrors)} rows. Use force_recalculate=True to recalculate.")
            return self.dfErrors
        
        logger.info("Detecting ROI count mismatches...")
        
        # Check if required columns exist
        required_columns = ['Cell ID', 'Condition', 'ROI Label']
        missing_columns = [col for col in required_columns if col not in self.dfMean.columns]
        if missing_columns:
            logger.error(f"Cannot detect ROI count mismatches: missing required columns: {missing_columns}")
            self.dfErrors = pd.DataFrame()
            return self.dfErrors
        
        # Group by Cell ID and Condition, count unique ROI Labels
        roi_counts = self.dfMean.groupby(['Cell ID', 'Condition'])['ROI Label'].nunique().reset_index()
        roi_counts = roi_counts.rename(columns={'ROI Label': 'ROI_Count'})
        
        # Find Cell IDs that have different ROI counts across conditions
        cell_roi_counts = roi_counts.groupby('Cell ID')['ROI_Count'].nunique()
        cells_with_mismatches = cell_roi_counts[cell_roi_counts > 1].index.tolist()
        
        errors_list = []
        
        for cell_id in cells_with_mismatches:
            # Get the ROI counts for this cell across all conditions
            cell_data = roi_counts[roi_counts['Cell ID'] == cell_id]
            
            # Create a dictionary of condition -> ROI count
            condition_roi_counts = dict(zip(cell_data['Condition'], cell_data['ROI_Count']))
            
            # Create error message
            conditions = list(condition_roi_counts.keys())
            roi_counts_list = list(condition_roi_counts.values())
            
            # Find the condition with the most ROIs for the error message
            max_roi_condition = max(condition_roi_counts, key=condition_roi_counts.get)
            max_roi_count = condition_roi_counts[max_roi_condition]
            
            # Find a condition with fewer ROIs for comparison
            other_conditions = [c for c in conditions if c != max_roi_condition]
            if other_conditions:
                other_condition = other_conditions[0]
                other_count = condition_roi_counts[other_condition]
                error_message = f"{cell_id} {max_roi_condition} has {max_roi_count} ROIs but {other_condition} has {other_count}"
            else:
                error_message = f"{cell_id} has inconsistent ROI counts across conditions: {condition_roi_counts}"
            
            # Create error record
            error_record = {
                'Error Type': 'ROI Count Mismatch',
                'Cell ID': cell_id,
                'Error Message': error_message,
                'Conditions': str(conditions),
                'ROI Counts': str(condition_roi_counts),
                'Timestamp': pd.Timestamp.now().isoformat()
            }
            errors_list.append(error_record)
        
        # Create DataFrame from errors
        if errors_list:
            self.dfErrors = pd.DataFrame(errors_list)
        else:
            self.dfErrors = pd.DataFrame()
        

        
        logger.info(f"Detected {len(self.dfErrors)} ROI count mismatch errors")
        return self.dfErrors

    def validate_df_mean_structure(self) -> Dict[str, Any]:
        """
        Validate the structure and data quality of the mean DataFrame.
        
        Returns
        -------
        Dict[str, Any]
            Validation results including issues found and recommendations
        """
        validation = {
            'is_valid': True,
            'issues': [],
            'warnings': [],
            'recommendations': []
        }
        
        if len(self.dfMean) == 0:
            validation['is_valid'] = False
            validation['issues'].append("dfMean is empty")
            return validation
        
        # Check for required columns
        required_columns = ['Cell ID', 'Condition', 'ROI Label', 'Number of Peaks']
        missing_required = [col for col in required_columns if col not in self.dfMean.columns]
        if missing_required:
            validation['is_valid'] = False
            validation['issues'].append(f"Missing required columns: {missing_required}")
        
        # Check for groups with very few peaks
        if 'Number of Peaks' in self.dfMean.columns:
            low_peak_groups = self.dfMean[self.dfMean['Number of Peaks'] < 3]
            if len(low_peak_groups) > 0:
                validation['warnings'].append(f"{len(low_peak_groups)} groups have fewer than 3 peaks")
                validation['recommendations'].append("Consider excluding groups with <3 peaks for statistical reliability")
        
        # Check for high CV values (indicating high variability)
        cv_columns = [col for col in self.dfMean.columns if col.endswith('_cv')]
        for cv_col in cv_columns:
            high_cv = self.dfMean[self.dfMean[cv_col] > 50]  # CV > 50%
            if len(high_cv) > 0:
                validation['warnings'].append(f"{len(high_cv)} groups have high CV (>50%) for {cv_col}")
        
        # Check for missing values in key columns
        key_columns = ['Peak Height_mean', 'Peak Inst Freq (Hz)_mean', 'Rise Time (ms)_mean']
        for col in key_columns:
            if col in self.dfMean.columns:
                missing_count = self.dfMean[col].isna().sum()
                if missing_count > 0:
                    validation['warnings'].append(f"{missing_count} missing values in {col}")
        
        return validation

    def get_condition_comparison(self, metric: str, condition1: str, condition2: str) -> Dict[str, Any]:
        """
        Compare a specific metric between two conditions.
        
        Parameters
        ----------
        metric : str
            The metric to compare (e.g., 'Peak Height_mean', 'Peak Inst Freq (Hz)_mean')
        condition1 : str
            First condition name
        condition2 : str
            Second condition name
            
        Returns
        -------
        Dict[str, Any]
            Comparison statistics including t-test results if applicable
        """
        if len(self.dfMean) == 0:
            logger.warning("Cannot compare conditions: dfMean is empty")
            return {}
        
        if metric not in self.dfMean.columns:
            logger.warning(f"Metric '{metric}' not found in dfMean columns")
            return {}
        
        # Filter data for each condition
        cond1_data = self.dfMean[self.dfMean['Condition'] == condition1][metric].dropna()
        cond2_data = self.dfMean[self.dfMean['Condition'] == condition2][metric].dropna()
        
        if len(cond1_data) == 0 or len(cond2_data) == 0:
            logger.warning(f"Insufficient data for comparison: {condition1} (n={len(cond1_data)}), {condition2} (n={len(cond2_data)})")
            return {}
        
        # Calculate basic statistics
        comparison = {
            'metric': metric,
            'condition1': condition1,
            'condition2': condition2,
            'n1': len(cond1_data),
            'n2': len(cond2_data),
            'mean1': cond1_data.mean(),
            'mean2': cond2_data.mean(),
            'std1': cond1_data.std(),
            'std2': cond2_data.std(),
            'sem1': cond1_data.sem(),
            'sem2': cond2_data.sem(),
            'difference': cond1_data.mean() - cond2_data.mean(),
            'percent_change': ((cond1_data.mean() - cond2_data.mean()) / cond2_data.mean()) * 100
        }
        
        # Perform t-test if we have enough data
        if len(cond1_data) >= 2 and len(cond2_data) >= 2:
            try:
                from scipy import stats
                t_stat, p_value = stats.ttest_ind(cond1_data, cond2_data)
                comparison['t_statistic'] = t_stat
                comparison['p_value'] = p_value
                comparison['significant'] = p_value < 0.05
            except ImportError:
                logger.warning("scipy not available for t-test")
            except Exception as e:
                logger.warning(f"T-test failed: {e}")
        
        return comparison

    def get_statistical_summary(self, metric, group_by=None):
        """
        Generate a statistical summary table for a given metric, grouped by a specified column.
        Args:
            metric (str): The column to summarize.
            group_by (str, optional): The column to group by. Defaults to the first group_column.
        Returns:
            pd.DataFrame: Summary statistics for each group.
        """
        if len(self.dfMean) == 0:
            logger.warning("Cannot create statistical summary: dfMean is empty")
            return pd.DataFrame()
        
        if metric not in self.dfMean.columns:
            logger.warning(f"Metric '{metric}' not found in dfMean columns")
            return pd.DataFrame()
        
        if group_by not in self.dfMean.columns:
            logger.warning(f"Group column '{group_by}' not found in dfMean columns")
            return pd.DataFrame()
        
        # Group by the specified column and calculate statistics using NaN-aware functions
        summary = self.dfMean.groupby(group_by)[metric].agg([
            ('n', lambda x: x.count()),      # Count non-NaN values
            ('mean', lambda x: x.mean()),    # NaN-aware mean
            ('std', lambda x: x.std()),      # NaN-aware std
            ('sem', lambda x: x.sem()),      # NaN-aware sem
            ('median', lambda x: x.median()), # NaN-aware median
            ('min', lambda x: x.min()),      # NaN-aware min
            ('max', lambda x: x.max())       # NaN-aware max
        ]).reset_index()
        
        # Rename columns for clarity
        summary.columns = [group_by, 'n', 'mean', 'std', 'sem', 'median', 'min', 'max']
        
        return summary

    def get_df_mean(self, force_recalculate: bool = False) -> pd.DataFrame:
        """
        Get the mean DataFrame, creating it if it doesn't exist.
        
        Parameters
        ----------
        force_recalculate : bool, optional
            If True, recalculate the mean DataFrame. Default is False.
            
        Returns
        -------
        pd.DataFrame
            The mean DataFrame
        """
        if len(self.dfMean) == 0 or force_recalculate:
            self.create_df_mean(force_recalculate=force_recalculate)
        else:
            # Ensure filter columns exist even if dfMean already exists
            self._add_filter_columns()
        return self.dfMean.copy()

    def get_df_errors(self, force_recalculate: bool = False) -> pd.DataFrame:
        """
        Get the errors DataFrame, detecting errors if needed.
        
        Parameters
        ----------
        force_recalculate : bool, optional
            If True, recalculate errors even if dfErrors already exists. Default is False.
            
        Returns
        -------
        pd.DataFrame
            The errors DataFrame
        """
        if len(self.dfErrors) == 0 or force_recalculate:
            # First ensure we have dfMean
            self.get_df_mean(force_recalculate)
            # Then detect errors
            self.detect_roi_count_mismatches(force_recalculate)
        
        return self.dfErrors.copy()

    def refresh_df_errors(self):
        """Refresh the errors DataFrame by recalculating it from the current dfMean."""
        logger.info("Refreshing dfErrors...")
        self.detect_roi_count_mismatches(force_recalculate=True)

    def refresh_df_mean(self, affected_groups: Optional[List[Tuple]] = None):
        """
        Refresh the mean DataFrame by recalculating it from the current master_df.
        
        Parameters
        ----------
        affected_groups : Optional[List[Tuple]], optional
            List of (Cell ID, Condition, ROI Label, Channel) tuples that were affected.
            If provided, only these groups will be updated. If None, all groups are recalculated.
        """
        if affected_groups is None:
            # Full refresh - recalculate everything
            logger.info("Refreshing dfMean (full recalculation)...")
            self.create_df_mean(force_recalculate=True)
        else:
            # Partial refresh - only update affected groups
            logger.info(f"Refreshing dfMean for {len(affected_groups)} affected groups...")
            logger.info(f'  affected_groups:{affected_groups}')
            self._refresh_df_mean_partial(affected_groups)
    
    def _refresh_df_mean_partial(self, affected_groups: List[Tuple]):
        """
        Partially refresh the mean DataFrame by only updating specific groups.
        
        Parameters
        ----------
        affected_groups : List[Tuple]
            List of (Cell ID, Condition, ROI Label, Channel) tuples to update
        """
        if len(self.master_df) == 0 or len(self.dfMean) == 0:
            # If either dataframe is empty, do a full refresh
            self.create_df_mean(force_recalculate=True)
            return
        
        # Check if required columns exist
        missing_columns = [col for col in self._group_columns if col not in self.master_df.columns]
        if missing_columns:
            logger.error(f"Cannot refresh dfMean: missing required columns: {missing_columns}")
            return
        
        # Filter to only include columns that actually exist in master_df
        available_numeric_columns = [col for col in self._numeric_columns if col in self.master_df.columns]
        
        # For each affected group, recalculate its statistics
        for group_tuple in affected_groups:
            if len(group_tuple) != len(self._group_columns):
                logger.warning(f"Invalid group tuple: {group_tuple}, expected {len(self._group_columns)} values")
                continue
            
            # Create a mask for this group in master_df
            group_mask = pd.Series(True, index=self.master_df.index)
            for i, col in enumerate(self._group_columns):
                group_mask &= (self.master_df[col] == group_tuple[i])
            
            # Get the data for this group
            group_data = self.master_df[group_mask]
            
            if len(group_data) == 0:
                # Group no longer exists in master_df, remove from dfMean
                df_mean_mask = pd.Series(True, index=self.dfMean.index)
                for i, col in enumerate(self._group_columns):
                    df_mean_mask &= (self.dfMean[col] == group_tuple[i])
                self.dfMean = self.dfMean[~df_mean_mask]
                logger.debug(f"Removed group {group_tuple} from dfMean (no data in master_df)")
                continue
            
            # Calculate statistics for this group
            if not available_numeric_columns:
                # Just count peaks
                new_row = {
                    'Number of Peaks': len(group_data),
                    'Area Under Peak (Sum)': np.nan
                }
            else:
                # Calculate full statistics
                new_row = {}
                for col in available_numeric_columns:
                    values = group_data[col].dropna()
                    if len(values) > 0:
                        new_row[col] = values.mean()
                        new_row[f"{col}_std"] = values.std()
                        new_row[f"{col}_sem"] = values.sem()
                        new_row[f"{col}_median"] = values.median()
                        new_row[f"{col}_min"] = values.min()
                        new_row[f"{col}_max"] = values.max()
                        # Calculate CV for key metrics
                        if col in ['Peak Height', 'Peak Inst Interval (s)', 'Peak Inst Freq (Hz)', 
                                  'Rise Time (ms)', 'Decay Time (ms)', 'Area Under Peak']:
                            if values.mean() != 0:
                                new_row[f"{col}_cv"] = (values.std() / values.mean()) * 100
                        if col == 'Area Under Peak':
                            new_row['Area Under Peak (Sum)'] = values.sum()
                # If Area Under Peak was not present, set as NaN
                if 'Area Under Peak (Sum)' not in new_row:
                    new_row['Area Under Peak (Sum)'] = np.nan
                new_row['Number of Peaks'] = len(group_data)
            
            # Add grouping columns
            for i, col in enumerate(self._group_columns):
                new_row[col] = group_tuple[i]
            
            # Add metadata columns (take first value from group)
            metadata_columns = ['Region', 'Date', 'Repeat', 'Analysis Type', 'Polarity', 'Tif Rel Path']
            for col in metadata_columns:
                if col in group_data.columns:
                    new_row[col] = group_data[col].iloc[0]
            
            # Find if this group already exists in dfMean
            df_mean_mask = pd.Series(True, index=self.dfMean.index)
            for i, col in enumerate(self._group_columns):
                df_mean_mask &= (self.dfMean[col] == group_tuple[i])
            
            if df_mean_mask.any():
                # Update existing row
                row_idx = df_mean_mask.idxmax()
                for col, value in new_row.items():
                    if col in self.dfMean.columns:
                        self.dfMean.at[row_idx, col] = value
                logger.debug(f"Updated group {group_tuple} in dfMean")
            else:
                # Add new row
                new_df = pd.DataFrame([new_row])
                self.dfMean = pd.concat([self.dfMean, new_df], ignore_index=True)
                logger.debug(f"Added new group {group_tuple} to dfMean")
        
        # Ensure filter columns exist
        self._add_filter_columns()
        
        # Auto-save the mean data
        self._auto_save_mean_data()

    def get_mean_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics for the mean DataFrame.
        
        Returns
        -------
        Dict[str, Any]
            Summary statistics including counts and ranges
        """
        if len(self.dfMean) == 0:
            return {
                'total_groups': 0,
                'total_peaks': 0,
                'unique_cells': 0,
                'unique_conditions': 0,
                'unique_regions': 0
            }
        
        summary = {
            'total_groups': len(self.dfMean),
            'total_peaks': self.dfMean['Number of Peaks'].sum() if 'Number of Peaks' in self.dfMean.columns else 0,
            'unique_cells': len(self.dfMean['Cell ID'].unique()) if 'Cell ID' in self.dfMean.columns else 0,
            'unique_conditions': len(self.dfMean['Condition'].unique()) if 'Condition' in self.dfMean.columns else 0,
            'unique_regions': len(self.dfMean['Region'].unique()) if 'Region' in self.dfMean.columns else 0,
        }
        
        # Add peak count statistics
        if 'Number of Peaks' in self.dfMean.columns:
            summary['peaks_per_group'] = {
                'mean': self.dfMean['Number of Peaks'].mean(),
                'std': self.dfMean['Number of Peaks'].std(),
                'min': self.dfMean['Number of Peaks'].min(),
                'max': self.dfMean['Number of Peaks'].max()
            }
        
        return summary

    def filter_df_mean_by_condition(self, condition: str) -> pd.DataFrame:
        """
        Filter the mean DataFrame by condition.
        
        Parameters
        ----------
        condition : str
            Condition to filter by
            
        Returns
        -------
        pd.DataFrame
            Filtered mean DataFrame
        """
        if len(self.dfMean) == 0:
            return pd.DataFrame()
        
        if 'Condition' not in self.dfMean.columns:
            logger.warning("No 'Condition' column found in dfMean")
            return pd.DataFrame()
        
        return self.dfMean[self.dfMean['Condition'] == condition]

    def filter_df_mean_by_region(self, region: str) -> pd.DataFrame:
        """
        Filter the mean DataFrame by region.
        
        Parameters
        ----------
        region : str
            Region to filter by
            
        Returns
        -------
        pd.DataFrame
            Filtered mean DataFrame
        """
        if len(self.dfMean) == 0:
            return pd.DataFrame()
        
        if 'Region' not in self.dfMean.columns:
            logger.warning("No 'Region' column found in dfMean")
            return pd.DataFrame()
        
        return self.dfMean[self.dfMean['Region'] == region]

    def export_df_mean_to_csv(self, filepath: str, filters: Optional[Dict[str, Any]] = None):
        """
        Export the mean DataFrame to CSV file.
        
        Parameters
        ----------
        filepath : str
            Path to save the CSV file
        filters : Optional[Dict[str, Any]], optional
            Dictionary of column-value pairs to filter by
        """
        df_to_export = self.get_df_mean().copy()
        
        if filters:
            for column, value in filters.items():
                if column in df_to_export.columns:
                    df_to_export = df_to_export[df_to_export[column] == value]
        
        df_to_export.to_csv(filepath, index=False)
        logger.info(f"Exported {len(df_to_export)} mean rows to: {filepath}")

    def pool_all_analysis(self, progress_callback=None):
        """Pool analysis results from all files in the backend using lazy KymRoiAnalysis loading."""
        logger.info("Pooling analysis results from all files...")
        all_results = []
        df = self.tif_file_backend.df
        if df is None or len(df) == 0:
            logger.warning("No files found in backend.")
            return
        total_files = len(df)
        if progress_callback:
            progress_callback.update(0, f"Starting analysis of {total_files} files...")
        processed = 0
        for idx, row in df.iterrows():
            rel_path = row['relative_path']
            kym_analysis = self.tif_file_backend.get_kym_roi_analysis(idx)
            if kym_analysis is None:
                continue
            processed += 1
            # Update progress
            if progress_callback:
                progress_callback.update(processed, f"Processing file {processed}/{total_files}: {Path(rel_path).name}")
            for channel in range(kym_analysis.numChannels):
                # Intensity
                intensity_df = kym_analysis.getDataFrame(channel, PeakDetectionTypes.intensity)
                if len(intensity_df) > 0:
                    if 'Analysis Type' not in intensity_df.columns:
                        intensity_df['Analysis Type'] = 'Intensity'
                    intensity_df['Channel'] = channel
                    intensity_df['Tif Rel Path'] = rel_path
                    intensity_df['TIF Filename'] = Path(rel_path).name
                    intensity_df['Date'] = row['Date']
                    intensity_df['Cell ID'] = row['Cell ID']
                    intensity_df['Region'] = row['Region']
                    intensity_df['Condition'] = row['Condition']
                    intensity_df['Repeat'] = row['Repeat']
                    
                    for roi in kym_analysis.getRoiLabels():
                        polarity = kym_analysis.getDetectionParams(roi, PeakDetectionTypes.intensity, channel)['Polarity']
                        intensity_df.loc[intensity_df['ROI Label'] == roi, 'Polarity'] = polarity
                    all_results.append(intensity_df)
        if all_results:
            self.master_df = pd.concat(all_results, ignore_index=True)
            if len(self.master_df) > 0 and 'ROI Label' in self.master_df.columns:
                unique_roi_labels = self.master_df['ROI Label'].unique()
                logger.info(f"After pooling: ROI Label data types: {[type(label) for label in unique_roi_labels]}")
                logger.info(f"After pooling: Sample ROI labels: {unique_roi_labels[:5]}")
        else:
            self.master_df = pd.DataFrame()
        self._auto_save_pooled_data()
        
        # Refresh dfMean after updating master_df
        if len(self.master_df) > 0:
            logger.info(f"Refreshing dfMean from {len(self.master_df)} master rows...")
            self.refresh_df_mean()
            # Also refresh errors after updating mean data
            self.refresh_df_errors()
            logger.info(f"dfMean refresh complete. dfMean has {len(self.dfMean)} rows.")
        else:
            logger.warning("No master data to create dfMean from")
        
        _resultStr = f"Pooling complete. Master DataFrame has {len(self.master_df)} rows."
        if progress_callback:
            progress_callback.complete(_resultStr)
        else:
            logger.info(_resultStr)

    def update_from_analysis(self, tif_path: str) -> bool:
        """Update pool with analysis results from a specific file.
        
        Parameters
        ----------
        tif_path : str
            Path to the TIF file to update analysis from (can be absolute or relative).
            The method will automatically find the file in the backend regardless of path type.
            
        Returns
        -------
        bool
            True if analysis was successfully updated, False otherwise
        """
        try:
            # Validate input path
            if not tif_path or tif_path.strip() == "":
                logger.error(f"Invalid tif_path provided: '{tif_path}'")
                return False
            
            # Find the row index in the backend DataFrame using helper method
            row_index = self._find_file_by_path(tif_path)
            if row_index is None:
                logger.warning(f"File not found in backend: {tif_path}")
                return False
            
            # Get the KymRoiAnalysis object for this file
            kym_analysis = self.tif_file_backend.get_kym_roi_analysis(row_index)
            if kym_analysis is None:
                logger.warning(f"Failed to load KymRoiAnalysis for {tif_path}")
                return False
            
            # Remove existing data for this file from the master DataFrame
            self._remove_file_from_pool(tif_path)
            
            # Add new analysis results for this file
            new_results = []
            for channel in range(kym_analysis.numChannels):
                # Intensity analysis
                intensity_df = kym_analysis.getDataFrame(channel, PeakDetectionTypes.intensity)
                if len(intensity_df) > 0:
                    # Only add columns that don't already exist in the KymRoiAnalysis DataFrame
                    if 'Analysis Type' not in intensity_df.columns:
                        intensity_df['Analysis Type'] = 'Intensity'
                    # Add Channel column - this is required for grouping
                    intensity_df['Channel'] = channel
                    # Add file identification columns - use the relative_path from backend
                    rel_path = self.tif_file_backend.df.at[row_index, 'relative_path']
                    intensity_df['Tif Rel Path'] = rel_path
                    intensity_df['TIF Filename'] = Path(rel_path).name
                    
                    # Add key metadata columns from TifFileBackend's COLUMN_CONFIG
                    intensity_df['Date'] = self.tif_file_backend.df.at[row_index, 'Date']
                    intensity_df['Cell ID'] = self.tif_file_backend.df.at[row_index, 'Cell ID']
                    intensity_df['Region'] = self.tif_file_backend.df.at[row_index, 'Region']
                    intensity_df['Condition'] = self.tif_file_backend.df.at[row_index, 'Condition']
                    intensity_df['Repeat'] = self.tif_file_backend.df.at[row_index, 'Repeat']
                    
                    new_results.append(intensity_df)
                # Diameter analysis (commented out for now)
                # diameter_df = kym_analysis.getDataFrame(channel, PeakDetectionTypes.diameter)
                # if len(diameter_df) > 0:
                #     diameter_df['Analysis Type'] = 'Diameter'
                #     diameter_df['Channel'] = channel
                #     diameter_df['TIF Path'] = resolved_path
                #     diameter_df['TIF Filename'] = os.path.basename(tif_path)
                #     new_results.append(diameter_df)
            
            # Add new results to master DataFrame
            if new_results:
                new_df = pd.concat(new_results, ignore_index=True)
                
                # Identify which groups will be affected by this update
                affected_groups = []
                if len(new_df) > 0:
                    # Get unique groups from the new data
                    affected_groups = new_df[self._group_columns].drop_duplicates().values.tolist()
                    # Convert to tuples for the refresh method
                    affected_groups = [tuple(group) for group in affected_groups]
                
                if len(self.master_df) == 0:
                    self.master_df = new_df
                else:
                    self.master_df = pd.concat([self.master_df, new_df], ignore_index=True)
                
                # Auto-save after updating analysis
                self._auto_save_pooled_data()
                
                # Refresh dfMean after updating master_df - only affected groups
                if len(self.master_df) > 0:
                    self.refresh_df_mean(affected_groups=affected_groups)
                    # Also refresh errors after updating mean data
                    self.refresh_df_errors()
                
                logger.info(f"Updated analysis for {tif_path}: added {len(new_df)} rows, refreshed {len(affected_groups)} groups")
                return True
            else:
                logger.warning(f"No analysis results found for {tif_path}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update analysis for {tif_path}: {e}")
            return False

    def on_analysis_saved(self, tif_path: str) -> bool:
        """
        Called when a KymRoiAnalysis is saved to update both backend metadata and pooled data.
        
        This method should be called from TifTableView when it receives a signal that
        analysis has been saved for a specific TIF file.
        
        Parameters
        ----------
        tif_path : str
            Path to the TIF file that was just analyzed and saved (can be absolute or relative).
            The method will automatically find the file in the backend regardless of path type.
            
        Returns
        -------
        bool
            True if both backend and pool were successfully updated, False otherwise
        """
        logger.info(f"Processing saved analysis for: {tif_path}")
        
        # First, update the backend's analysis-related columns
        backend_updated = self.tif_file_backend.update_analysis(tif_path)
        if not backend_updated:
            logger.warning(f"Failed to update backend for {tif_path}")
            # Continue anyway, as the pooled data might still be updated
        
        # Then, update the pooled analysis data
        pool_updated = self.update_from_analysis(tif_path)
        if not pool_updated:
            logger.warning(f"Failed to update pooled data for {tif_path}")
        
        success = backend_updated and pool_updated
        if success:
            logger.info(f"Successfully updated both backend and pool for {tif_path}")
        else:
            logger.warning(f"Partial update for {tif_path}: backend={backend_updated}, pool={pool_updated}")
        
        return success

    def refresh_analysis(self, tif_paths: List[str] = None):
        """Refresh analysis for specific files or all files.
        
        Parameters
        ----------
        tif_paths : List[str], optional
            List of TIF file paths to refresh (can be absolute or relative).
            The method will automatically find files in the backend regardless of path type.
            If None, refreshes all files.
        """
        if tif_paths is None:
            # Refresh all files
            logger.info("Refreshing analysis for all files...")
            df = self.tif_file_backend.df
            if df is None or len(df) == 0:
                logger.warning("No files found in backend.")
                return
            
            # Clear existing pooled data
            self.master_df = pd.DataFrame()
            
            # Pool all analysis
            self.pool_all_analysis()
        else:
            # Refresh specific files
            if isinstance(tif_paths, str):
                # Handle single string path
                tif_paths = [tif_paths]
            
            logger.info(f"Refreshing analysis for {len(tif_paths)} files...")
            for tif_path in tif_paths:
                if not tif_path or tif_path.strip() == "":
                    logger.warning(f"Skipping empty or invalid path: '{tif_path}'")
                    continue
                success = self.update_from_analysis(tif_path)
                if not success:
                    logger.warning(f"Failed to refresh analysis for {tif_path}")
        
        logger.info("Analysis refresh complete.")

    def _remove_file_from_pool(self, tif_path: str):
        """Remove all analysis results for a specific file from the master DataFrame.
        
        Parameters
        ----------
        tif_path : str
            Path to the TIF file to remove (can be absolute or relative)
        """
        if len(self.master_df) == 0:
            return
            
        # Find the relative path for this file in the backend
        row_index = self._find_file_by_path(tif_path)
        if row_index is None:
            logger.warning(f"File not found in backend for removal: {tif_path}")
            return
            
        rel_path = self.tif_file_backend.df.at[row_index, 'relative_path']
        
        # Remove rows where Tif Rel Path matches
        initial_count = len(self.master_df)
        
        # Get the groups that will be affected before removing data
        affected_groups = []
        if len(self.master_df) > 0:
            # Get unique groups from the data being removed
            removed_data = self.master_df[self.master_df['Tif Rel Path'] == rel_path]
            if len(removed_data) > 0:
                affected_groups = removed_data[self._group_columns].drop_duplicates().values.tolist()
                affected_groups = [tuple(group) for group in affected_groups]
        
        self.master_df = self.master_df[self.master_df['Tif Rel Path'] != rel_path]
        removed_count = initial_count - len(self.master_df)
        
        if removed_count > 0:
            logger.debug(f"Removed {removed_count} rows for {tif_path} from pool")
            # Auto-save after removing data
            self._auto_save_pooled_data()
            
            # Refresh dfMean after updating master_df - only affected groups
            if len(self.master_df) > 0:
                self.refresh_df_mean(affected_groups=affected_groups)
                # Also refresh errors after updating mean data
                self.refresh_df_errors()

    def update_roi_label(self, oldRoiLabel: str, newRoiLabel: str) -> bool:
        """Update ROI labels in both master_df and dfMean when an ROI label is changed.
        
        Parameters
        ----------
        oldRoiLabel : str
            The old ROI label to replace
        newRoiLabel : str
            The new ROI label to use
            
        Returns
        -------
        bool
            True if the update was successful, False otherwise
        """
        if len(self.master_df) == 0:
            logger.warning("Cannot update ROI label: master_df is empty")
            return False
            
        if 'ROI Label' not in self.master_df.columns:
            logger.warning("Cannot update ROI label: 'ROI Label' column not found in master_df")
            return False
        
        # Check if the new ROI label already exists in the data
        if newRoiLabel in self.master_df['ROI Label'].unique():
            logger.warning(f"Cannot update ROI label: '{newRoiLabel}' already exists in the data")
            return False
        
        # Update master_df
        initial_master_count = len(self.master_df)
        self.master_df.loc[self.master_df['ROI Label'] == oldRoiLabel, 'ROI Label'] = newRoiLabel
        updated_master_count = len(self.master_df[self.master_df['ROI Label'] == newRoiLabel])
        
        if updated_master_count == 0:
            logger.warning(f"No rows found with old ROI label '{oldRoiLabel}' in master_df")
            return False
        
        logger.info(f"Updated {updated_master_count} rows in master_df from '{oldRoiLabel}' to '{newRoiLabel}'")
        
        # Auto-save master_df after updating
        self._auto_save_pooled_data()
        
        # Update dfMean if it exists
        if len(self.dfMean) > 0 and 'ROI Label' in self.dfMean.columns:
            initial_mean_count = len(self.dfMean)
            self.dfMean.loc[self.dfMean['ROI Label'] == oldRoiLabel, 'ROI Label'] = newRoiLabel
            updated_mean_count = len(self.dfMean[self.dfMean['ROI Label'] == newRoiLabel])
            
            if updated_mean_count > 0:
                logger.info(f"Updated {updated_mean_count} rows in dfMean from '{oldRoiLabel}' to '{newRoiLabel}'")
                
                # Auto-save dfMean after updating
                self._auto_save_mean_data()
            else:
                logger.warning(f"No rows found with old ROI label '{oldRoiLabel}' in dfMean")
        
        # Refresh dfMean to ensure consistency (this will recalculate statistics)
        if len(self.master_df) > 0:
            # Get the affected groups for efficient refresh
            affected_groups = []
            if len(self.dfMean) > 0:
                # Find groups that contain the new ROI label
                affected_data = self.master_df[self.master_df['ROI Label'] == newRoiLabel]
                if len(affected_data) > 0:
                    affected_groups = affected_data[self._group_columns].drop_duplicates().values.tolist()
                    affected_groups = [tuple(group) for group in affected_groups]
            
            # Refresh dfMean with affected groups
            self.refresh_df_mean(affected_groups=affected_groups)
            
            # Also refresh errors after updating mean data
            self.refresh_df_errors()
        
        logger.info(f"Successfully updated ROI label from '{oldRoiLabel}' to '{newRoiLabel}' in TiffPool")
        return True

    def update_roi_label_for_file(self, oldRoiLabel: str, newRoiLabel: str, tif_path: str) -> bool:
        """Update ROI labels in both master_df and dfMean for a specific TIF file when an ROI label is changed.
        
        Parameters
        ----------
        oldRoiLabel : str
            The old ROI label to replace
        newRoiLabel : str
            The new ROI label to use
        tif_path : str
            The TIF file path (can be absolute or relative)
            
        Returns
        -------
        bool
            True if the update was successful, False otherwise
        """
        if len(self.master_df) == 0:
            logger.warning("Cannot update ROI label: master_df is empty")
            return False
            
        if 'ROI Label' not in self.master_df.columns:
            logger.warning("Cannot update ROI label: 'ROI Label' column not found in master_df")
            return False
        
        if 'Tif Rel Path' not in self.master_df.columns:
            logger.warning("Cannot update ROI label: 'Tif Rel Path' column not found in master_df")
            return False
        
        # Find the relative path for this file in the backend
        row_index = self._find_file_by_path(tif_path)
        if row_index is None:
            logger.warning(f"File not found in backend for ROI label update: {tif_path}")
            return False
            
        rel_path = self.tif_file_backend.df.at[row_index, 'relative_path']
        logger.info(f"Found relative path for ROI label update: {rel_path}")
        
        # Check if the new ROI label already exists in the data for this specific file
        file_data = self.master_df[self.master_df['Tif Rel Path'] == rel_path]
        if newRoiLabel in file_data['ROI Label'].unique():
            logger.warning(f"Cannot update ROI label: '{newRoiLabel}' already exists in file {rel_path}")
            return False
        
        # Update master_df - only for the specific file
        file_mask = self.master_df['Tif Rel Path'] == rel_path
        roi_mask = self.master_df['ROI Label'] == oldRoiLabel
        combined_mask = file_mask & roi_mask
        
        rows_to_update = self.master_df[combined_mask]
        if len(rows_to_update) == 0:
            # Debug: Check what ROI labels actually exist in the file data
            file_data = self.master_df[self.master_df['Tif Rel Path'] == rel_path]
            if len(file_data) > 0:
                unique_roi_labels = file_data['ROI Label'].unique()
                logger.warning(f"No rows found with old ROI label '{oldRoiLabel}' in file {rel_path}")
                logger.warning(f"Available ROI labels in this file: {unique_roi_labels}")
                logger.warning(f"ROI label types: {[type(label) for label in unique_roi_labels]}")
                
                # Try converting the oldRoiLabel to different types to see if there's a type mismatch
                try:
                    # Try as integer
                    roi_mask_int = self.master_df['ROI Label'] == int(oldRoiLabel)
                    combined_mask_int = file_mask & roi_mask_int
                    rows_to_update_int = self.master_df[combined_mask_int]
                    if len(rows_to_update_int) > 0:
                        logger.info(f"Found {len(rows_to_update_int)} rows when converting '{oldRoiLabel}' to int")
                        # Use the integer version
                        roi_mask = roi_mask_int
                        combined_mask = combined_mask_int
                        rows_to_update = rows_to_update_int
                    else:
                        logger.warning(f"No rows found even when converting '{oldRoiLabel}' to int")
                except (ValueError, TypeError):
                    logger.warning(f"Could not convert '{oldRoiLabel}' to int")
            else:
                logger.warning(f"No data found for file {rel_path}")
            return False
        
        # Update the ROI labels
        self.master_df.loc[combined_mask, 'ROI Label'] = newRoiLabel
        updated_count = len(rows_to_update)
        
        logger.info(f"Updated {updated_count} rows in master_df from '{oldRoiLabel}' to '{newRoiLabel}' for file {rel_path}")
        
        # Auto-save master_df after updating
        self._auto_save_pooled_data()
        
        # Update dfMean if it exists - only for groups that contain this file's data
        if len(self.dfMean) > 0 and 'ROI Label' in self.dfMean.columns:
            # Get the groups that contain data from this file
            file_groups = file_data[self._group_columns].drop_duplicates().values.tolist()
            file_groups = [tuple(group) for group in file_groups]
            
            # Update dfMean for these groups
            for group_tuple in file_groups:
                if len(group_tuple) == len(self._group_columns):
                    # Create a mask for this group in dfMean
                    df_mean_mask = pd.Series(True, index=self.dfMean.index)
                    for i, col in enumerate(self._group_columns):
                        df_mean_mask &= (self.dfMean[col] == group_tuple[i])
                    
                    # Update ROI Label for this group if it matches the old label
                    roi_mask = self.dfMean['ROI Label'] == oldRoiLabel
                    combined_mask = df_mean_mask & roi_mask
                    
                    if combined_mask.any():
                        self.dfMean.loc[combined_mask, 'ROI Label'] = newRoiLabel
                        logger.info(f"Updated dfMean for group {group_tuple} from '{oldRoiLabel}' to '{newRoiLabel}'")
            
            # Auto-save dfMean after updating
            self._auto_save_mean_data()
        
        # Refresh dfMean to ensure consistency (this will recalculate statistics)
        if len(self.master_df) > 0:
            # Get the affected groups for efficient refresh
            affected_groups = []
            if len(self.dfMean) > 0:
                # Find groups that contain the new ROI label for this file
                # Recreate the mask since the DataFrame has been modified
                file_mask = self.master_df['Tif Rel Path'] == rel_path
                roi_mask = self.master_df['ROI Label'] == newRoiLabel
                new_combined_mask = file_mask & roi_mask
                
                affected_data = self.master_df[new_combined_mask]
                if len(affected_data) > 0:
                    affected_groups = affected_data[self._group_columns].drop_duplicates().values.tolist()
                    affected_groups = [tuple(group) for group in affected_groups]
            
            # Refresh dfMean with affected groups
            self.refresh_df_mean(affected_groups=affected_groups)
            
            # Also refresh errors after updating mean data
            self.refresh_df_errors()
        
        logger.info(f"Successfully updated ROI label from '{oldRoiLabel}' to '{newRoiLabel}' for file {rel_path} in TiffPool")
        return True

    def save_pooled_data(self):
        """Save pooled data to CSV file in the loaded folder."""
        if len(self.master_df) > 0:
            filepath = self._get_pooled_data_filepath()
            try:
                # self.master_df.to_csv(filepath, index=False)
                with open(filepath,'w') as f:
                    # save self._headerDict as json
                    f.write(json.dumps(self._headerDict) + '\n')
                    self.master_df.to_csv(f, index=False)
                logger.debug(f"Saved pooled data to: {filepath} ({len(self.master_df)} rows)")
                return filepath
            except Exception as e:
                logger.error(f"Failed to save pooled data to {filepath}: {e}")
                return None
        else:
            logger.debug("No pooled data to save (master_df is empty)")
            return None

    def get_master_dataframe(self) -> pd.DataFrame:
        return self.master_df.copy()

    def get_analysis_summary(self) -> Dict[str, Any]:
        if len(self.master_df) == 0:
            return {
                'total_peaks': 0,
                'total_files': 0,
                'analysis_types': [],
                'channels': [],
                'date_range': None
            }
        summary = {
            'total_peaks': len(self.master_df),
            'total_files': len(self.master_df['Tif Rel Path'].unique()),
            'analysis_types': self.master_df['Analysis Type'].unique().tolist(),
            'channels': sorted(self.master_df['Channel'].unique().tolist()),
        }
        if 'Date' in self.master_df.columns:
            dates = pd.to_datetime(self.master_df['Date'], errors='coerce')
            valid_dates = dates.dropna()
            if len(valid_dates) > 0:
                summary['date_range'] = {
                    'start': valid_dates.min().strftime('%Y-%m-%d'),
                    'end': valid_dates.max().strftime('%Y-%m-%d')
                }
        return summary

    def filter_by_condition(self, condition: str) -> pd.DataFrame:
        df = self.tif_file_backend.df
        if 'Condition' not in df.columns:
            logger.warning("No 'Condition' column found in backend DataFrame")
            return pd.DataFrame()
        rel_paths = set(df[df['Condition'] == condition]['relative_path'])
        return self.master_df[self.master_df['Tif Rel Path'].isin(rel_paths)]

    def filter_by_region(self, region: str) -> pd.DataFrame:
        df = self.tif_file_backend.df
        if 'Region' not in df.columns:
            logger.warning("No 'Region' column found in backend DataFrame")
            return pd.DataFrame()
        rel_paths = set(df[df['Region'] == region]['relative_path'])
        return self.master_df[self.master_df['Tif Rel Path'].isin(rel_paths)]

    def get_unique_values(self, column: str) -> List[str]:
        df = self.tif_file_backend.df
        if column not in df.columns:
            logger.warning(f"Column '{column}' not found in backend DataFrame")
            return []
        return df[column].unique().tolist()

    def export_to_csv(self, filepath: str, filters: Optional[Dict[str, Any]] = None):
        df_to_export = self.master_df.copy()
        if filters:
            for column, value in filters.items():
                if column in df_to_export.columns:
                    df_to_export = df_to_export[df_to_export[column] == value]
        df_to_export.to_csv(filepath, index=False)
        logger.info(f"Exported {len(df_to_export)} rows to: {filepath}")

    def get_available_metrics(self) -> List[str]:
        """
        Get list of available metrics in the mean DataFrame.
        
        Returns
        -------
        List[str]
            List of metric column names (those ending with _mean)
        """
        if len(self.dfMean) == 0:
            return []
        
        # Get all columns that end with _mean (these are our calculated metrics)
        metrics = [col for col in self.dfMean.columns if col.endswith('_mean')]
        return sorted(metrics)

    def get_available_conditions(self) -> List[str]:
        """
        Get list of available conditions in the mean DataFrame.
        
        Returns
        -------
        List[str]
            List of unique condition values
        """
        if len(self.dfMean) == 0 or 'Condition' not in self.dfMean.columns:
            return []
        
        return sorted(self.dfMean['Condition'].unique().tolist())

    def filter_df_mean_by_multiple_conditions(self, conditions: List[str]) -> pd.DataFrame:
        """
        Filter the mean DataFrame by multiple conditions.
        
        Parameters
        ----------
        conditions : List[str]
            List of conditions to include
            
        Returns
        -------
        pd.DataFrame
            Filtered mean DataFrame
        """
        if len(self.dfMean) == 0:
            return pd.DataFrame()
        
        if 'Condition' not in self.dfMean.columns:
            logger.warning("No 'Condition' column found in dfMean")
            return pd.DataFrame()
        
        return self.dfMean[self.dfMean['Condition'].isin(conditions)]

    def detect_outliers(self, metric: str, method: str = 'iqr', threshold: float = 1.5) -> pd.DataFrame:
        """
        Detect outliers in a specific metric using various methods.
        
        Parameters
        ----------
        metric : str
            The metric to check for outliers (e.g., 'Peak Height_mean')
        method : str, optional
            Method for outlier detection: 'iqr' (interquartile range) or 'zscore'
        threshold : float, optional
            Threshold for outlier detection (default: 1.5 for IQR, 3 for z-score)
            
        Returns
        -------
        pd.DataFrame
            DataFrame containing only the outlier rows
        """
        if len(self.dfMean) == 0:
            logger.warning("Cannot detect outliers: dfMean is empty")
            return pd.DataFrame()
        
        if metric not in self.dfMean.columns:
            logger.warning(f"Metric '{metric}' not found in dfMean columns")
            return pd.DataFrame()
        
        data = self.dfMean[metric].dropna()
        if len(data) == 0:
            logger.warning(f"No valid data for outlier detection in {metric}")
            return pd.DataFrame()
        
        outliers_mask = pd.Series(False, index=self.dfMean.index)
        
        if method.lower() == 'iqr':
            # IQR method
            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - threshold * IQR
            upper_bound = Q3 + threshold * IQR
            
            outliers_mask = (self.dfMean[metric] < lower_bound) | (self.dfMean[metric] > upper_bound)
            
        elif method.lower() == 'zscore':
            # Z-score method
            z_scores = abs((data - data.mean()) / data.std())
            outliers_mask = z_scores > threshold
            
        else:
            logger.warning(f"Unknown outlier detection method: {method}")
            return pd.DataFrame()
        
        outliers_df = self.dfMean[outliers_mask].copy()
        
        if len(outliers_df) > 0:
            logger.info(f"Found {len(outliers_df)} outliers in {metric} using {method} method")
        else:
            logger.info(f"No outliers found in {metric} using {method} method")
        
        return outliers_df

    def export_filtered_df_mean(self, filepath: str, 
                               conditions: Optional[List[str]] = None,
                               regions: Optional[List[str]] = None,
                               min_peaks: Optional[int] = None,
                               exclude_outliers: Optional[str] = None,
                               format_options: Optional[Dict[str, Any]] = None) -> bool:
        """
        Export filtered mean DataFrame with various filtering options.
        
        Parameters
        ----------
        filepath : str
            Path to save the CSV file
        conditions : Optional[List[str]], optional
            List of conditions to include
        regions : Optional[List[str]], optional
            List of regions to include
        min_peaks : Optional[int], optional
            Minimum number of peaks required per group
        exclude_outliers : Optional[str], optional
            Metric to use for outlier detection and exclusion
        format_options : Optional[Dict[str, Any]], optional
            Additional formatting options for the export
            
        Returns
        -------
        bool
            True if export was successful, False otherwise
        """
        try:
            df_to_export = self.get_df_mean().copy()
            
            # Apply filters
            if conditions:
                df_to_export = df_to_export[df_to_export['Condition'].isin(conditions)]
                logger.info(f"Filtered by conditions: {conditions}")
            
            if regions:
                df_to_export = df_to_export[df_to_export['Region'].isin(regions)]
                logger.info(f"Filtered by regions: {regions}")
            
            if min_peaks is not None:
                df_to_export = df_to_export[df_to_export['Number of Peaks'] >= min_peaks]
                logger.info(f"Filtered by minimum peaks: {min_peaks}")
            
            if exclude_outliers:
                outliers_df = self.detect_outliers(exclude_outliers)
                if len(outliers_df) > 0:
                    # Remove outlier rows
                    outlier_indices = outliers_df.index
                    df_to_export = df_to_export.drop(outlier_indices)
                    logger.info(f"Excluded {len(outliers_df)} outliers based on {exclude_outliers}")
            
            # Apply formatting if specified
            if format_options:
                if 'round_decimals' in format_options:
                    decimals = format_options['round_decimals']
                    if not df_to_export.empty:
                        numeric_columns = [col for col in df_to_export.select_dtypes(include=[np.number]).columns if col in df_to_export.columns]
                        if numeric_columns:
                            df_to_export[numeric_columns] = df_to_export[numeric_columns].round(decimals)
                
                if 'sort_by' in format_options:
                    sort_columns = format_options['sort_by']
                    if isinstance(sort_columns, str):
                        sort_columns = [sort_columns]
                    df_to_export = df_to_export.sort_values(sort_columns)
            
            # Export to CSV
            df_to_export.to_csv(filepath, index=False)
            logger.info(f"Exported {len(df_to_export)} filtered mean rows to: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export filtered dfMean: {e}")
            return False

    def get_df_mean_info(self) -> Dict[str, Any]:
        """
        Return metadata and summary info about the current mean DataFrame (dfMean).
        Useful for diagnostics and reporting.
        """
        if len(self.dfMean) == 0:
            return {
                'is_empty': True,
                'total_rows': 0,
                'total_columns': 0
            }
        
        info = {
            'is_empty': False,
            'total_rows': len(self.dfMean),
            'total_columns': len(self.dfMean.columns),
            'column_types': self.dfMean.dtypes.to_dict(),
            'available_metrics': self.get_available_metrics(),
            'available_conditions': self.get_available_conditions(),
            'available_regions': sorted(self.dfMean['Region'].unique().tolist()) if 'Region' in self.dfMean.columns else [],
            'peak_count_stats': {}
        }
        
        # Add peak count statistics
        if 'Number of Peaks' in self.dfMean.columns:
            peak_counts = self.dfMean['Number of Peaks']
            info['peak_count_stats'] = {
                'total_peaks': peak_counts.sum(),
                'mean_peaks_per_group': peak_counts.mean(),
                'std_peaks_per_group': peak_counts.std(),
                'min_peaks_per_group': peak_counts.min(),
                'max_peaks_per_group': peak_counts.max(),
                'groups_with_few_peaks': len(peak_counts[peak_counts < 3])
            }
        
        # Add validation results
        validation = self.validate_df_mean_structure()
        info['validation'] = validation
        
        return info 