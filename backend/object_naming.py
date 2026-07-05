"""Object name extraction and normalization utilities."""
import re
from pathlib import Path


def extract_object_name_from_path(file_path, base_path=None):
    """
    Extract object name from file path with priority: M > NGC > IC > Others > C.
    First checks inside parentheses, then the rest of the path.
    
    Args:
        file_path: Full path to the file
        base_path: Optional base path to strip before extracting (e.g., scan folder)
    
    Example: 'C19 (IC 5146,Cocoon Nebula)' should return 'IC5146'
    """
    path_str = str(file_path)
    
    # Strip base path if provided to get relative path
    if base_path:
        base_str = str(base_path)
        if path_str.startswith(base_str):
            path_str = path_str[len(base_str):].lstrip('/\\')
    
    # Extract all catalog references from the path
    found_objects = []
    
    # Patterns with priority order matching get_catalog_priority()
    # IMPORTANT: Order matters! More specific patterns (IC, NGC) must come before less specific (C)
    patterns = [
        (r'\bM\s*(\d+)', 'M', 0),              # Messier: highest priority
        (r'\bNGC\s*(\d+)', 'NGC', 1),          # NGC: second priority
        (r'\bIC\s*(\d+)', 'IC', 2),            # IC: third priority
        (r'\bCaldwell\s+(\d+)', 'C', 5),       # Caldwell long form (lowest priority)
        (r'\bC\s*(\d+)(?!\d)', 'C', 5),        # Caldwell short: lowest priority
        (r'\bSh2[-\s]*(\d+)', 'SH2-', 4),      # Sharpless
        (r'\bLDN\s*(\d+)', 'LDN', 4),          # Lynds Dark Nebula
        (r'\bAbell\s*(\d+)', 'ABELL', 4),      # Abell catalog
    ]
    
    # First, check inside parentheses (higher priority)
    paren_match = re.search(r'\(([^)]+)\)', path_str)
    if paren_match:
        paren_content = paren_match.group(1)
        for pattern, prefix, priority in patterns:
            matches = re.finditer(pattern, paren_content, re.IGNORECASE)
            for match in matches:
                number = match.group(1)
                obj_name = f"{prefix}{number}"
                # Give parentheses content higher priority (subtract 0.5)
                found_objects.append((priority - 0.5, obj_name))
    
    # Then check the entire path
    for pattern, prefix, priority in patterns:
        matches = re.finditer(pattern, path_str, re.IGNORECASE)
        for match in matches:
            number = match.group(1)
            obj_name = f"{prefix}{number}"
            # Check if we already found this from parentheses
            if not any(obj[1] == obj_name for obj in found_objects):
                found_objects.append((priority, obj_name))
    
    # Return the highest priority object found
    if found_objects:
        found_objects.sort(key=lambda x: x[0])
        return found_objects[0][1]
    
    return None


def get_catalog_priority(obj_name):
    """
    Get priority for catalog names. Lower number = higher priority.
    Priority: M (Messier) > NGC > IC > Others > C (Caldwell)
    """
    if not obj_name or obj_name == "Unknown":
        return 999
    
    obj_upper = obj_name.upper()
    if obj_upper.startswith('M') and obj_upper[1:].lstrip().isdigit():
        return 0  # Messier has highest priority
    elif obj_upper.startswith('NGC'):
        return 1  # NGC second
    elif obj_upper.startswith('IC'):
        return 2  # IC third
    elif obj_upper.startswith('C') and obj_upper[1:].lstrip().isdigit():
        return 5  # Caldwell lowest (before unknown)
    else:
        return 4  # Others


def normalize_object_name(object_name):
    """Normalize object name to primary identifier (e.g., 'M76 (NGC 650,...)' -> 'M76')."""
    if not object_name:
        return None

    # Remove everything after opening parenthesis or comma
    # This handles cases like "M76 (NGC 650,Little Dumbell,Cork,Butterfly Nebula)"
    object_name = object_name.split('(')[0].strip()
    object_name = object_name.split(',')[0].strip()

    # Common patterns for celestial objects - extract the primary identifier
    # IMPORTANT: Order matters! More specific patterns (IC, NGC) must come before less specific (C)
    patterns = [
        (r'\bM\s*(\d+)', 'M'),                 # Messier: M31, M 31
        (r'\bNGC\s*(\d+)', 'NGC'),             # NGC: NGC7000
        (r'\bCaldwell\s+(\d+)', 'C'),          # Caldwell long: Caldwell 14 -> C14
        (r'\bC\s*(\d+)(?!\d)', 'C'),           # Caldwell short: C14 (not followed by more digits)
        (r'\bIC\s*(\d+)', 'IC'),               # IC: IC1396
        (r'\bSh2[-\s]*(\d+)', 'SH2-'),         # Sharpless: Sh2-155
        (r'\bLDN\s*(\d+)', 'LDN'),             # Lynds Dark Nebula
        (r'\bAbell\s*(\d+)', 'ABELL'),         # Abell catalog
    ]

    for pattern, prefix in patterns:
        match = re.search(pattern, object_name, re.IGNORECASE)
        if match:
            number = match.group(1)
            return f"{prefix}{number}"

    # If no pattern matches, return cleaned name
    return object_name.strip().upper()


def extract_session_date_from_path(file_path, base_path=None):
    """
    Extract session date from path (format: YYYY-MM-DD).
    
    Args:
        file_path: Full path to the file
        base_path: Optional base path to strip before extracting (e.g., scan folder)
    """
    path_str = str(file_path)
    
    # Strip base path if provided to get relative path
    if base_path:
        base_str = str(base_path)
        if path_str.startswith(base_str):
            path_str = path_str[len(base_str):].lstrip('/\\')
    
    # Look for date pattern YYYY-MM-DD
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})', path_str)
    if match:
        return match.group(0)
    
    return None


def extract_descriptive_name_from_path(file_path, base_path=None):
    """
    Extract a descriptive name from the path when no catalog object is found.
    Priority:
    1. If path contains 'YYYY-MM-DD/Name' pattern, return 'Name'
    2. Otherwise, return the first/root folder name in the relative path
    
    Args:
        file_path: Full path to the file
        base_path: Optional base path to strip before extracting (e.g., scan folder)
    
    Examples:
    - '2025-03-14/Stack of Moon/file.fits' -> 'Stack of Moon'
    - 'darks/QHY5III715C/RAW8@3864x2192/15.0s/gain_20/file.fits' -> 'darks'
    - 'C:/base/darks/file.fits' (with base_path='C:/base') -> 'darks'
    - 'M31/session1/file.fits' -> 'M31'
    """
    path_str = str(file_path)
    
    # Strip base path if provided to get relative path
    if base_path:
        base_str = str(base_path)
        if path_str.startswith(base_str):
            path_str = path_str[len(base_str):].lstrip('/\\')
    
    path = Path(path_str)
    parts = path.parts
    
    # Need at least 2 parts (folder + file)
    if len(parts) < 2:
        return None
    
    # Look for a date folder in the path (YYYY-MM-DD pattern)
    date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}')
    
    for i, part in enumerate(parts):
        if date_pattern.match(part):
            # Found a date folder, check if there's a next part (the descriptive name)
            if i + 1 < len(parts):
                next_part = parts[i + 1]
                # Skip if it's a file
                if not next_part.lower().endswith(('.fits', '.fit', '.png', '.tif', '.tiff', '.jpg', '.jpeg')):
                    # Return just the descriptive name (not date/name)
                    return next_part
            # If the date folder is the last folder before the file, no descriptive name
            break
    
    # No date pattern found, use the first folder in the relative path
    for part in parts:
        # Skip if it's the filename itself
        if part.lower().endswith(('.fits', '.fit', '.png', '.tif', '.tiff', '.jpg', '.jpeg')):
            continue
        # This is the first actual folder name
        return part
    
    return None


def extract_fields_from_pattern(file_path, base_path, path_pattern):
    """Extract metadata fields from a file path using a PathPattern.
    
    Bridges the PathPattern extraction with existing normalization logic.
    
    Args:
        file_path: Full path to the file
        base_path: Base scan folder path
        path_pattern: A PathPattern instance
    
    Returns:
        Dictionary with keys like 'target_name', 'date', 'filter', 'session'
        or None if the pattern doesn't match or is empty.
        The 'target_name' value is run through normalize_object_name or
        extract_object_name_from_path for catalog name normalization.
    """
    if path_pattern is None or path_pattern.is_empty:
        return None
    
    extracted = path_pattern.extract(str(file_path), str(base_path) if base_path else None)
    if not extracted:
        return None
    
    # Normalize the target name through existing catalog recognition
    if 'target_name' in extracted and extracted['target_name']:
        raw_name = extracted['target_name']
        # First try to extract a catalog name from the folder name
        normalized = normalize_object_name(raw_name)
        if normalized and normalized != 'Unknown':
            extracted['target_name'] = normalized
        else:
            # Try the path-based extraction on the raw name
            catalog_name = extract_object_name_from_path(raw_name, None)
            if catalog_name:
                extracted['target_name'] = catalog_name
            # Otherwise keep the raw folder name as-is
    
    return extracted


def extract_catalog_number(obj_name):
    """Extract the numeric part from catalog names for cross-referencing."""
    if not obj_name:
        return None
    
    # Extract number from patterns like M31, NGC7000, C14, IC1396
    match = re.search(r'([A-Z]+)\s*(\d+)', obj_name.upper())
    if match:
        catalog, number = match.groups()
        return (catalog, int(number))
    return None
