#!/usr/bin/env python3
"""
TifInfo dataclass for parsing TIF file names.
"""

import re
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
import os

from sanpy.kym.logger import get_logger

logger = get_logger(__name__)

@dataclass
class TifInfo:
    """Dataclass to hold parsed file information from TIF file names.
    
    Example filenames:
        "20250312 ISAN R1 LS1.tif"
        "20250312 ISAN FCCP R1 LS1.tif"
        "20250312 ISAN R1 LS1_0001.tif"
    """
    date: str
    cellid: str
    condition: str
    region: str
    repeat: int
    error: str = ""
    
    # Class variables for configurable parsing
    POSSIBLE_CONDITIONS = ['Control', 'Ivab', 'Thap', 'FCCP']
    POSSIBLE_REGIONS = ['ISAN', 'SSAN']
    
    @classmethod
    def from_filename(cls, filename: str) -> 'TifInfo':
        """Create TifInfo from a TIF filename.
        
        Args:
            filename: Filename like "20250312 ISAN R1 LS1.tif" or "20250312 ISAN FCCP R1 LS1.tif"
            
        Returns:
            TifInfo object with parsed components
        """
        errors = []
        
        # Remove .tif extension if present
        clean_filename = filename.replace('.tif', '')
        
        # Normalize multiple spaces to single spaces
        # Handle cases like '  ' or '   ' becoming ' '
        while '  ' in clean_filename:
            clean_filename = clean_filename.replace('  ', ' ')
        
        # Split into parts
        parts = clean_filename.split(' ')
        
        # Validate minimum parts
        if len(parts) < 4:
            error_msg = f"Filename '{filename}' has insufficient parts (need at least 4, got {len(parts)})"
            logger.error(error_msg)
            errors.append(error_msg)
            return cls(
                date="",
                cellid="",
                condition="Control",  # default
                region="",
                repeat=0,
                error="; ".join(errors)
            )
        
        # Extract date (first part)
        date = parts[0]
        if not date.isdigit() or len(date) != 8:
            error_msg = f"Date '{date}' in filename '{filename}' is not a valid 8-digit date (YYYYMMDD)"
            logger.error(error_msg)
            errors.append(error_msg)
            date = ""
        
        # Extract region
        region = None
        for part in parts:
            if part in cls.POSSIBLE_REGIONS:
                region = part
                break
        
        if region is None:
            error_msg = f"Region not found in filename '{filename}'. Expected one of {cls.POSSIBLE_REGIONS}"
            logger.error(error_msg)
            errors.append(error_msg)
            region = ""
        
        # Extract condition
        condition = "Control"  # default
        for cond in cls.POSSIBLE_CONDITIONS:
            if cond in clean_filename:
                condition = cond
                break
        
        # Extract repeat number
        repeat = 0  # default
        # Look for pattern like _0001, _0002, etc. or spaces followed by 3-4 digits at the end
        repeat_pattern = r'[_\s](\d{3,4})$'  # underscore or space followed by 3-4 digits at the end
        repeat_match = re.search(repeat_pattern, clean_filename)
        if repeat_match:
            repeat_str = repeat_match.group(1)
            try:
                repeat = int(repeat_str)
            except ValueError:
                error_msg = f"Could not parse repeat number '{repeat_str}' from filename '{filename}'"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Extract cellid - everything up to the repeat pattern
        cellid_parts = clean_filename
        if repeat_match:
            # Remove the repeat pattern from the end
            cellid_parts = clean_filename[:repeat_match.start()]
        
        # Remove condition from cellid if present
        for cond in cls.POSSIBLE_CONDITIONS:
            if cond in cellid_parts:
                cellid_parts = cellid_parts.replace(f' {cond}', '')
                break
        
        cellid = cellid_parts.strip()
        
        # Validate cellid has expected format
        if not cellid or len(cellid.split(' ')) < 3:
            error_msg = f"CellID '{cellid}' from filename '{filename}' does not have expected format (should be like '20250312 ISAN R1 LS1')"
            logger.error(error_msg)
            errors.append(error_msg)
        
        return cls(
            date=date,
            cellid=cellid,
            condition=condition,
            region=region,
            repeat=repeat,
            error="; ".join(errors) if errors else ""
        )
    
    @classmethod
    def set_possible_conditions(cls, conditions: list) -> None:
        """Update the list of possible conditions for parsing.
        
        Args:
            conditions: List of condition strings to recognize
        """
        cls.POSSIBLE_CONDITIONS = conditions
    
    @classmethod
    def set_possible_regions(cls, regions: list) -> None:
        """Update the list of possible regions for parsing.
        
        Args:
            regions: List of region strings to recognize
        """
        cls.POSSIBLE_REGIONS = regions