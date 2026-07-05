"""
Module for writing metadata to FITS and PNG files.
"""
from pathlib import Path
from astropy.io import fits
from typing import Dict, Any, Optional
import json
import struct
import zlib


def save_metadata_to_fits(file_path: str, metadata: Dict[str, Any]) -> bool:
    """
    Save metadata to a FITS file header.
    
    Args:
        file_path: Path to the FITS file
        metadata: Dictionary containing metadata to save (ra, dec, object_name)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        with fits.open(file_path, mode='update') as hdul:
            hdr = hdul[0].header
            
            # Update OBJECT field if provided
            if 'object_name' in metadata and metadata['object_name']:
                hdr['OBJECT'] = metadata['object_name']
            
            # Update RA field if provided (in degrees)
            if 'ra' in metadata and metadata['ra'] is not None:
                hdr['RA'] = float(metadata['ra'])
                # Also update OBJCTRA in HMS format if ra_hms is provided
                if 'ra_hms' in metadata:
                    hdr['OBJCTRA'] = metadata['ra_hms']
            
            # Update DEC field if provided (in degrees)
            if 'dec' in metadata and metadata['dec'] is not None:
                hdr['DEC'] = float(metadata['dec'])
                # Also update OBJCTDEC in DMS format if dec_dms is provided
                if 'dec_dms' in metadata:
                    hdr['OBJCTDEC'] = metadata['dec_dms']
            
            # Flush changes to disk
            hdul.flush()
        
        print(f"Successfully saved metadata to FITS file: {file_path}")
        return True
    
    except Exception as e:
        print(f"Error saving metadata to FITS file {file_path}: {e}")
        return False


def _read_png_chunks(file_path: str):
    """Read PNG file and return list of chunks."""
    with open(file_path, 'rb') as f:
        # Verify PNG signature
        signature = f.read(8)
        if signature != b'\x89PNG\r\n\x1a\n':
            raise ValueError("Not a valid PNG file")
        
        chunks = []
        while True:
            # Read chunk length
            length_data = f.read(4)
            if len(length_data) < 4:
                break
            
            length = struct.unpack('>I', length_data)[0]
            
            # Read chunk type
            chunk_type = f.read(4)
            if len(chunk_type) < 4:
                break
            
            # Read chunk data
            data = f.read(length)
            
            # Read CRC
            crc = f.read(4)
            
            chunks.append({
                'type': chunk_type,
                'data': data,
                'crc': crc
            })
            
            # Stop after IEND chunk
            if chunk_type == b'IEND':
                break
        
        return chunks


def _write_png_chunks(file_path: str, chunks):
    """Write PNG file from list of chunks."""
    with open(file_path, 'wb') as f:
        # Write PNG signature
        f.write(b'\x89PNG\r\n\x1a\n')
        
        # Write all chunks
        for chunk in chunks:
            # Write length
            f.write(struct.pack('>I', len(chunk['data'])))
            
            # Write type
            f.write(chunk['type'])
            
            # Write data
            f.write(chunk['data'])
            
            # Calculate and write CRC
            crc_data = chunk['type'] + chunk['data']
            crc = zlib.crc32(crc_data) & 0xffffffff
            f.write(struct.pack('>I', crc))


def _create_itxt_chunk(keyword: str, text: str) -> dict:
    """
    Create an iTXt (international text) chunk for PNG.
    Format: keyword\0compression_flag\0compression_method\0language_tag\0translated_keyword\0text
    """
    # iTXt format for uncompressed text
    data = keyword.encode('latin-1')
    data += b'\x00'  # null separator
    data += b'\x00'  # compression flag (0 = uncompressed)
    data += b'\x00'  # compression method (must be 0 for uncompressed)
    data += b''      # language tag (empty)
    data += b'\x00'  # null separator
    data += b''      # translated keyword (empty)
    data += b'\x00'  # null separator
    data += text.encode('utf-8')  # text in UTF-8
    
    return {
        'type': b'iTXt',
        'data': data,
        'crc': None
    }


def save_metadata_to_png(file_path: str, metadata: Dict[str, Any]) -> bool:
    """
    Save metadata to a PNG file using both tEXt and iTXt chunks.
    - tEXt "Comment" chunk: JSON data for our app to read
    - iTXt "Description" chunk: Human-readable text for Windows Explorer
    Preserves original image data without recompression.
    
    Args:
        file_path: Path to the PNG file
        metadata: Dictionary containing metadata to save (ra, dec, object_name)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Read all chunks from the PNG file
        chunks = _read_png_chunks(file_path)
        
        # Find existing Comment and Description chunks
        existing_comment = None
        comment_index = None
        description_index = None
        
        for i, chunk in enumerate(chunks):
            if chunk['type'] == b'tEXt':
                # tEXt format: keyword\0text
                null_pos = chunk['data'].find(b'\x00')
                if null_pos > 0:
                    keyword = chunk['data'][:null_pos].decode('latin-1')
                    if keyword == 'Comment':
                        existing_comment = chunk['data'][null_pos + 1:].decode('latin-1')
                        comment_index = i
            elif chunk['type'] == b'iTXt':
                # iTXt format: keyword\0compression_flag\0compression_method\0language\0translated_keyword\0text
                null_pos = chunk['data'].find(b'\x00')
                if null_pos > 0:
                    keyword = chunk['data'][:null_pos].decode('latin-1')
                    if keyword == 'Description':
                        description_index = i
        
        # Parse existing comment as JSON
        try:
            existing_data = json.loads(existing_comment) if existing_comment else {}
        except:
            existing_data = {}
        
        # Update with new metadata
        if 'object_name' in metadata and metadata['object_name']:
            existing_data['OBJECT'] = metadata['object_name']
        
        if 'ra' in metadata and metadata['ra'] is not None:
            existing_data['RA'] = float(metadata['ra'])
            if 'ra_hms' in metadata:
                existing_data['OBJCTRA'] = metadata['ra_hms']
        
        if 'dec' in metadata and metadata['dec'] is not None:
            existing_data['DEC'] = float(metadata['dec'])
            if 'dec_dms' in metadata:
                existing_data['OBJCTDEC'] = metadata['dec_dms']
        
        # Create new Comment chunk (JSON for our app)
        comment_json = json.dumps(existing_data)
        comment_data = b'Comment\x00' + comment_json.encode('latin-1')
        
        comment_chunk = {
            'type': b'tEXt',
            'data': comment_data,
            'crc': None
        }
        
        # Create human-readable description for Windows Explorer
        description_parts = []
        if 'OBJECT' in existing_data:
            description_parts.append(f"Object: {existing_data['OBJECT']}")
        if 'OBJCTRA' in existing_data:
            description_parts.append(f"RA: {existing_data['OBJCTRA']}")
        if 'OBJCTDEC' in existing_data:
            description_parts.append(f"Dec: {existing_data['OBJCTDEC']}")
        
        description_text = ' | '.join(description_parts) if description_parts else comment_json
        description_chunk = _create_itxt_chunk('Description', description_text)
        
        # Replace or insert chunks
        if comment_index is not None:
            chunks[comment_index] = comment_chunk
        else:
            # Insert before IEND chunk
            chunks.insert(-1, comment_chunk)
        
        if description_index is not None:
            chunks[description_index] = description_chunk
        else:
            # Insert before IEND chunk
            chunks.insert(-1, description_chunk)
        
        # Write to temporary file first
        temp_path = str(file_path) + '.tmp'
        _write_png_chunks(temp_path, chunks)
        
        # Replace original file
        import os
        os.replace(temp_path, file_path)
        
        print(f"Successfully saved metadata to PNG file: {file_path}")
        return True
    
    except Exception as e:
        print(f"Error saving metadata to PNG file {file_path}: {e}")
        import traceback
        traceback.print_exc()
        return False


def read_metadata_from_png(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Read metadata from PNG Comment tEXt chunk.
    
    Args:
        file_path: Path to the PNG file
    
    Returns:
        Dictionary containing metadata or None if not found
    """
    try:
        chunks = _read_png_chunks(file_path)
        
        # Find Comment chunk
        for i, chunk in enumerate(chunks):
            chunk_type = chunk['type'].decode('latin-1') if isinstance(chunk['type'], bytes) else chunk['type']
            
            if chunk['type'] == b'tEXt':
                null_pos = chunk['data'].find(b'\x00')
                if null_pos > 0:
                    keyword = chunk['data'][:null_pos].decode('latin-1')
                    if keyword == 'Comment':
                        comment = chunk['data'][null_pos + 1:].decode('latin-1')
                        try:
                            metadata = json.loads(comment)
                            return metadata
                        except Exception as e:
                            return None
        
        return None
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None


def save_metadata_to_tiff(file_path: str, metadata: Dict[str, Any]) -> bool:
    """
    Save metadata to a TIFF file using the ImageDescription tag (270) in FITS header format.
    Uses tifffile library to preserve bit depth. Falls back to PIL for reading compressed TIFFs.
    
    Args:
        file_path: Path to the TIFF file
        metadata: Dictionary containing metadata to save (ra, dec, object_name)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        import tifffile
        import numpy as np
        
        image_data = None
        existing_description = ''
        use_pil_fallback = False
        
        # Try to read with tifffile first
        try:
            with tifffile.TiffFile(file_path) as tif:
                # Get existing ImageDescription if present
                page = tif.pages[0]
                existing_tags = page.tags
                if 'ImageDescription' in existing_tags:
                    existing_description = existing_tags['ImageDescription'].value
                
                # Try to get image data (this will fail if compressed and imagecodecs not available)
                try:
                    image_data = tif.asarray()
                except (ValueError, ImportError) as inner_e:
                    if 'imagecodecs' in str(inner_e) or 'COMPRESSION' in str(inner_e):
                        # Mark for PIL fallback after closing tifffile
                        use_pil_fallback = True
                    else:
                        raise
        except Exception as e:
            if 'imagecodecs' not in str(e) and 'COMPRESSION' not in str(e):
                raise
            use_pil_fallback = True
        
        # Use PIL fallback if needed
        if use_pil_fallback:
            print(f"[TIFF] Compressed TIFF detected, using PIL to read...")
            from PIL import Image
            img = Image.open(file_path)
            image_data = np.array(img)
            
            # Get existing ImageDescription from PIL
            existing_description = img.tag_v2.get(270, '')
            img.close()
        
        # Build FITS-style header string
        fits_lines = []
        
        # Preserve existing FITS header or start fresh
        if existing_description and 'FITS' in existing_description:
            # Keep existing header as base
            fits_lines.append(existing_description.strip())
        else:
            # Start with FITS marker
            fits_lines.append("FITS-style metadata")
        
        # Add/update metadata fields in FITS format
        if 'object_name' in metadata and metadata['object_name']:
            fits_lines.append(f"OBJECT  = '{metadata['object_name']}'")
        
        if 'ra' in metadata and metadata['ra'] is not None:
            fits_lines.append(f"RA      = {metadata['ra']}")
            if 'ra_hms' in metadata:
                # Convert to ASCII-safe format
                ra_hms_ascii = metadata['ra_hms'].replace('°', 'd').replace('′', "'").replace('″', '"')
                fits_lines.append(f"OBJCTRA = '{ra_hms_ascii}'")
        
        if 'dec' in metadata and metadata['dec'] is not None:
            fits_lines.append(f"DEC     = {metadata['dec']}")
            if 'dec_dms' in metadata:
                # Convert to ASCII-safe format (replace Unicode symbols)
                dec_dms_ascii = metadata['dec_dms'].replace('°', 'd').replace('′', "'").replace('″', '"')
                fits_lines.append(f"OBJCTDEC= '{dec_dms_ascii}'")
        
        # Join with separator
        description = ' / '.join(fits_lines)
        
        print(f"[TIFF SAVE DEBUG] Writing description: {description}")
        
        # Save to temporary file with metadata
        temp_path = str(file_path) + '.tmp'
        
        # Write TIFF with original data and new metadata
        # Always save without compression to avoid needing imagecodecs
        tifffile.imwrite(
            temp_path,
            image_data,
            compression=None,  # No compression
            description=description,
            photometric='rgb' if image_data.ndim == 3 else 'minisblack',
            metadata=None
        )
        
        # Replace original file
        import os
        os.replace(temp_path, file_path)
        
        print(f"Successfully saved metadata to TIFF file: {file_path}")
        return True
    
    except ImportError:
        print("ERROR: tifffile library not available. Cannot write TIFF metadata without it.")
        print("Install with: pip install tifffile")
        return False
    
    except Exception as e:
        print(f"Error saving metadata to TIFF file {file_path}: {e}")
        import traceback
        traceback.print_exc()
        return False


def save_metadata(file_path: str, metadata: Dict[str, Any]) -> bool:
    """
    Save metadata to a file (FITS, PNG, or TIFF).
    
    Args:
        file_path: Path to the file
        metadata: Dictionary containing metadata to save
    
    Returns:
        True if successful, False otherwise
    """
    file_ext = Path(file_path).suffix.lower()
    
    if file_ext in ['.fits', '.fit', '.fts']:
        return save_metadata_to_fits(file_path, metadata)
    elif file_ext == '.png':
        return save_metadata_to_png(file_path, metadata)
    elif file_ext in ['.tif', '.tiff']:
        return save_metadata_to_tiff(file_path, metadata)
    else:
        print(f"Unsupported file type for metadata writing: {file_ext}")
        return False
