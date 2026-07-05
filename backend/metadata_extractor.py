"""Metadata extraction from FITS and image files."""
import re
import time
from pathlib import Path
from astropy.io import fits
from .object_naming import (
    normalize_object_name, 
    extract_object_name_from_path,
    extract_session_date_from_path,
    extract_descriptive_name_from_path,
    extract_fields_from_pattern
)
from .astrometry import extract_astrometry_data, parse_fits_header_from_string


def extract_meta(file_path, base_path=None, path_pattern=None):
    """
    Read FITS header for UI display.
    
    Args:
        file_path: Full path to the FITS file
        base_path: Optional base path to strip for relative path extraction
        path_pattern: Optional PathPattern instance for pattern-based extraction
    """
    try:
        with fits.open(file_path) as hdul:
            hdr = hdul[0].header
            object_name = hdr.get("OBJECT", None)

            # Normalize object name from header (only for catalog objects)
            if object_name and object_name != "Unknown":
                object_name = normalize_object_name(object_name)

            # Try pattern-based extraction from path
            pattern_fields = extract_fields_from_pattern(file_path, base_path, path_pattern)

            # If no object in header, use pattern or fallback
            if not object_name or object_name == "Unknown":
                if pattern_fields and 'target_name' in pattern_fields:
                    object_name = pattern_fields['target_name']
                else:
                    object_name = extract_object_name_from_path(file_path, base_path)

            # If still no catalog object found, try descriptive name from path
            # Note: descriptive names are NOT normalized to preserve original case/spacing
            if not object_name:
                object_name = extract_descriptive_name_from_path(file_path, base_path)

            # Final fallback to Unknown
            if not object_name:
                object_name = "Unknown"

            # Session date: pattern first, then fallback
            if pattern_fields and 'date' in pattern_fields:
                session_date = pattern_fields['date']
            else:
                session_date = extract_session_date_from_path(file_path, base_path)
            
            # Extract astrometry data
            astrometry = extract_astrometry_data(hdr)
            
            # Filter: pattern first, then header
            filter_name = hdr.get("FILTER", "L")
            if pattern_fields and 'filter' in pattern_fields and filter_name == "L":
                filter_name = pattern_fields['filter']

            meta = {
                "path": str(file_path),
                "filename": Path(file_path).name,
                "object": object_name,
                "telescope": hdr.get("TELESCOP", "N/A"),
                "instrument": hdr.get("INSTRUME", "N/A"),
                "exptime": float(hdr.get("EXPTIME", 0)),
                "filter": filter_name,
                "date": hdr.get("DATE-OBS", "N/A"),
                "session_date": session_date,
                "file_type": "fits"
            }
            
            # Add pattern extraction source info
            if pattern_fields:
                meta['_extraction_source'] = 'pattern'
            
            # Add astrometry data if available
            if astrometry:
                meta['astrometry'] = astrometry
            
            return meta
    except Exception as e:
        print(f"Error extracting metadata from {file_path}: {e}")
        return {"error": str(e), "path": str(file_path)}


def extract_meta_from_image(file_path, base_path=None, path_pattern=None):
    """
    Extract metadata from processed image files (PNG, TIFF) based on path and TIFF tags.
    
    Args:
        file_path: Full path to the image file
        base_path: Optional base path to strip for relative path extraction
        path_pattern: Optional PathPattern instance for pattern-based extraction
    """
    # Try pattern-based extraction first
    pattern_fields = extract_fields_from_pattern(file_path, base_path, path_pattern)
    
    if pattern_fields and 'target_name' in pattern_fields:
        object_name = pattern_fields['target_name']
    else:
        object_name = extract_object_name_from_path(file_path, base_path)
    
    # If no catalog object found, try descriptive name from path
    # Note: descriptive names are NOT normalized to preserve original case/spacing
    if not object_name:
        object_name = extract_descriptive_name_from_path(file_path, base_path)
    
    # Final fallback
    if not object_name:
        object_name = "Unknown"
    
    # Session date: pattern first, then fallback
    if pattern_fields and 'date' in pattern_fields:
        session_date = pattern_fields['date']
    else:
        session_date = extract_session_date_from_path(file_path, base_path)
    
    # Filter from pattern
    filter_name = "N/A"
    if pattern_fields and 'filter' in pattern_fields:
        filter_name = pattern_fields['filter']
    
    file_ext = Path(file_path).suffix.lower()
    
    meta = {
        "path": str(file_path),
        "filename": Path(file_path).name,
        "object": object_name,
        "telescope": "N/A",
        "instrument": "N/A",
        "exptime": 0,
        "filter": filter_name,
        "date": "N/A",
        "session_date": session_date,
        "file_type": file_ext.replace('.', '')
    }
    
    # Add pattern extraction source info
    if pattern_fields:
        meta['_extraction_source'] = 'pattern'
    
    # Try to extract metadata from PNG Comments field
    if file_ext == '.png':
        try:
            from PIL import Image
            
            # Open image and check for text chunks
            img = Image.open(file_path)
            
            # PIL doesn't automatically load all tEXt chunks into img.info
            # We need to manually extract them from the PNG chunks
            comment_data = None
            
            # Try to get Comment from img.info first (in case it's there)
            if 'Comment' in img.info:
                try:
                    import json
                    comment_data = json.loads(img.info['Comment'])
                except Exception as e:
                    print(f"Failed to parse Comment from PIL: {e}")

            # If not found in img.info, use our custom reader
            if not comment_data:
                from .metadata_writer import read_metadata_from_png
                comment_data = read_metadata_from_png(file_path)
            
            img.close()
            
            if comment_data:
                # Extract object name
                if 'OBJECT' in comment_data:
                    obj_from_comment = normalize_object_name(comment_data['OBJECT'])
                    if obj_from_comment and obj_from_comment != "Unknown":
                        meta['object'] = obj_from_comment
                
                # Extract astrometry data
                astrometry = {}
                if 'RA' in comment_data:
                    astrometry['ra'] = float(comment_data['RA'])
                if 'DEC' in comment_data:
                    astrometry['dec'] = float(comment_data['DEC'])
                if astrometry:
                    meta['astrometry'] = astrometry
                
                # Extract other metadata if present
                if 'INSTRUME' in comment_data:
                    meta['instrument'] = comment_data['INSTRUME']
                if 'EXPTIME' in comment_data:
                    meta['exptime'] = float(comment_data['EXPTIME'])
                if 'DATE-OBS' in comment_data:
                    meta['date'] = comment_data['DATE-OBS']

        except Exception as e:
            import traceback
            traceback.print_exc()
    
    # Try to extract FITS header from TIFF description tag
    if file_ext in ['.tif', '.tiff']:
        try:
            from PIL import Image
            from PIL.TiffImagePlugin import TiffImageFile
            
            img = Image.open(file_path)
            if isinstance(img, TiffImageFile):
                # Check for FITS header in description tag (270)
                if 270 in img.tag_v2:
                    description = img.tag_v2[270]
                    if description and 'FITS' in description:
                        # Parse FITS-like header from description
                        astrometry = parse_fits_header_from_string(description)
                        if astrometry:
                            meta['astrometry'] = astrometry
                        
                        # Try to extract basic metadata from the header string
                        if 'OBJECT' in description:
                            match = re.search(r"OBJECT\s*=\s*'([^']+)'", description)
                            if match:
                                obj_from_header = normalize_object_name(match.group(1).strip())
                                if obj_from_header and obj_from_header != "Unknown":
                                    meta['object'] = obj_from_header
                        
                        if 'INSTRUME' in description:
                            match = re.search(r"INSTRUME\s*=\s*'([^']+)'", description)
                            if match:
                                meta['instrument'] = match.group(1).strip()
                        
                        if 'EXPTIME' in description:
                            match = re.search(r"EXPTIME\s*=\s*([\d.]+)", description)
                            if match:
                                meta['exptime'] = float(match.group(1))
                        
                        if 'DATE-OBS' in description:
                            match = re.search(r"DATE-OBS\s*=\s*'([^']+)'", description)
                            if match:
                                meta['date'] = match.group(1).strip()
            
            img.close()
        except Exception as e:
            print(f"Error extracting TIFF metadata from {file_path}: {e}")
    
    return meta
