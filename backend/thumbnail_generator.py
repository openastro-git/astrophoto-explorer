"""Thumbnail generation for FITS and image files."""
import hashlib
import numpy as np
from pathlib import Path
from astropy.io import fits
from astropy.visualization import ZScaleInterval
from PIL import Image
from .cache_manager import THUMBS_DIR, ensure_cache_dirs


def get_file_hash(file_path):
    """Generate a hash for a file based on path and modification time."""
    stat = Path(file_path).stat()
    hash_input = f"{file_path}_{stat.st_mtime}_{stat.st_size}"
    return hashlib.md5(hash_input.encode()).hexdigest()


def generate_thumbnail(file_path, thumb_size=(300, 300)):
    """Generate and cache a thumbnail for a file."""
    ensure_cache_dirs()

    file_hash = get_file_hash(file_path)
    thumb_path = THUMBS_DIR / f"{file_hash}.jpg"

    # Return cached thumbnail if exists
    if thumb_path.exists():
        return str(thumb_path)

    try:
        file_ext = Path(file_path).suffix.lower()

        # Handle FITS files
        if file_ext in ['.fits', '.fit', '.fts']:
            hdul = None
            try:
                hdul = fits.open(file_path, memmap=True)

                # Find first HDU with image data
                data = None
                for hdu in hdul:
                    try:
                        if hdu.data is not None and len(hdu.data.shape) >= 2:
                            data = hdu.data
                            break
                    except ValueError as e:
                        if "BZERO/BSCALE/BLANK" in str(e):
                            # Reload without memmap
                            hdul.close()
                            hdul = fits.open(file_path, memmap=False)
                            for hdu2 in hdul:
                                if hdu2.data is not None and len(hdu2.data.shape) >= 2:
                                    data = hdu2.data
                                    break
                            break
                        raise

            except (ValueError, OSError) as e:
                if "BZERO/BSCALE/BLANK" in str(e):
                    if hdul:
                        hdul.close()
                    hdul = fits.open(file_path, memmap=False)
                    for hdu in hdul:
                        if hdu.data is not None and len(hdu.data.shape) >= 2:
                            data = hdu.data
                            break
                else:
                    raise

            try:
                if data is None:
                    return None

                # Handle 3D data
                if len(data.shape) == 3:
                    if data.shape[0] == 3:
                        data = np.transpose(data, (1, 2, 0))
                    elif data.shape[0] < data.shape[1]:
                        data = data[0]
                    else:
                        data = data[data.shape[0] // 2]

                # Downsample large images before processing for speed
                # Only process at most 1000x1000 pixels for thumbnails
                if data.shape[0] > 1000 or data.shape[1] > 1000:
                    # Simple downsampling by slicing (much faster than interpolation)
                    step_y = max(1, data.shape[0] // 1000)
                    step_x = max(1, data.shape[1] // 1000)
                    if data.ndim == 2:
                        data = data[::step_y, ::step_x]
                    else:
                        data = data[::step_y, ::step_x, :]

                # Generate preview using Z-scale
                if data.ndim == 2:
                    interval = ZScaleInterval()
                    vmin, vmax = interval.get_limits(data)
                    normalized = ((data - vmin) / (vmax - vmin) * 255).clip(0, 255).astype('uint8')
                    img = Image.fromarray(normalized, mode='L')
                else:
                    # RGB data
                    preview = np.zeros((*data.shape[:2], 3), dtype=np.uint8)
                    for i in range(min(3, data.shape[2])):
                        interval = ZScaleInterval()
                        vmin, vmax = interval.get_limits(data[:, :, i])
                        preview[:, :, i] = ((data[:, :, i] - vmin) / (vmax - vmin) * 255).clip(0, 255).astype('uint8')
                    img = Image.fromarray(preview, mode='RGB')
            finally:
                if hdul:
                    hdul.close()

        # Handle image files
        elif file_ext in ['.png', '.tif', '.tiff']:
            img = Image.open(file_path)
            if img.mode not in ['RGB', 'L']:
                img = img.convert('RGB')
        else:
            return None

        # Create square thumbnail by cropping center
        # First resize to fit the smallest dimension to thumb_size
        img_width, img_height = img.size
        target_size = thumb_size[0]  # 300x300
        
        # Calculate scaling to make smallest dimension = target_size
        scale = target_size / min(img_width, img_height)
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        # Resize image
        img = img.resize((new_width, new_height), Image.Resampling.BILINEAR)
        
        # Crop center to make it square
        left = (new_width - target_size) // 2
        top = (new_height - target_size) // 2
        right = left + target_size
        bottom = top + target_size
        
        img = img.crop((left, top, right, bottom))
        
        # Save thumbnail
        img.save(thumb_path, 'JPEG', quality=80, optimize=False)

        return str(thumb_path)

    except Exception as e:
        print(f"Error generating thumbnail for {file_path}: {e}")
        return None
