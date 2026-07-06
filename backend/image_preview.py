"""Image preview generation with different sizes and stretch options."""

import json
import numpy as np
from io import BytesIO
from pathlib import Path
from astropy.io import fits
from astropy.visualization import ZScaleInterval
from PIL import Image
from .stretch import auto_stretch_unlinked, auto_stretch_linked, generate_preview_mtf
from .metadata_extractor import extract_meta, extract_meta_from_image

CONFIG_FILE = Path("config.json")


def load_stretch_settings():
    """Load stretch settings from config file."""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                return config.get("stretch", {})
    except Exception as e:
        print(f"Error loading stretch settings: {e}")

    # Return defaults if config doesn't exist or has no stretch settings
    return {"target_background": 0.17, "shadows_clipping": -2.8, "contrast_boost": 1.1, "linked_channels": True}


def generate_preview(data):
    """Normalize 32-bit FITS data to 8-bit for Web Canvas using Z-Scale."""
    interval = ZScaleInterval()
    vmin, vmax = interval.get_limits(data)
    normalized = ((data - vmin) / (vmax - vmin) * 255).clip(0, 255).astype("uint8")
    return normalized


def get_image_info(file_path):
    """Get image dimensions and metadata without loading full data."""
    try:
        file_ext = Path(file_path).suffix.lower()

        if file_ext in [".fits", ".fit", ".fts"]:
            hdul = None
            try:
                hdul = fits.open(file_path, memmap=True)

                # Find first HDU with image data
                for hdu in hdul:
                    try:
                        if hdu.data is not None and len(hdu.data.shape) >= 2:
                            shape = hdu.data.shape
                            header = hdu.header

                            return {
                                "width": shape[1] if len(shape) >= 2 else shape[0],
                                "height": shape[0],
                                "channels": shape[2] if len(shape) == 3 else 1,
                                "bitpix": header.get("BITPIX", -32),
                                "file_type": "fits",
                            }
                    except ValueError as e:
                        if "BZERO/BSCALE/BLANK" in str(e):
                            # Reload without memmap
                            hdul.close()
                            hdul = fits.open(file_path, memmap=False)
                            if hdu.data is not None and len(hdu.data.shape) >= 2:
                                shape = hdu.data.shape
                                header = hdu.header

                                return {
                                    "width": shape[1] if len(shape) >= 2 else shape[0],
                                    "height": shape[0],
                                    "channels": shape[2] if len(shape) == 3 else 1,
                                    "bitpix": header.get("BITPIX", -32),
                                    "file_type": "fits",
                                }
                        raise

                return {"error": "No image data in FITS file"}
            except (ValueError, OSError) as e:
                if "BZERO/BSCALE/BLANK" in str(e):
                    if hdul:
                        hdul.close()
                    hdul = fits.open(file_path, memmap=False)
                    for hdu in hdul:
                        if hdu.data is not None and len(hdu.data.shape) >= 2:
                            shape = hdu.data.shape
                            header = hdu.header

                            return {
                                "width": shape[1] if len(shape) >= 2 else shape[0],
                                "height": shape[0],
                                "channels": shape[2] if len(shape) == 3 else 1,
                                "bitpix": header.get("BITPIX", -32),
                                "file_type": "fits",
                            }
                    return {"error": "No image data in FITS file"}
                raise
            finally:
                if hdul:
                    hdul.close()

        elif file_ext in [".png", ".tif", ".tiff"]:
            img = Image.open(file_path)
            return {
                "width": img.width,
                "height": img.height,
                "channels": len(img.getbands()),
                "file_type": file_ext.replace(".", ""),
            }

        else:
            return {"error": f"Unsupported file type: {file_ext}"}

    except Exception as e:
        return {"error": str(e)}


def get_fits_preview(file_path, size="medium", stretch="mtf"):
    """
    Generate a preview image with different size and stretch options.

    Args:
        file_path: Path to the image file
        size: "thumbnail" (300px), "medium" (800px), "large" (1600px), "full"
        stretch: "zscale" or "mtf" (default)

    Returns:
        Dictionary with base64 image and metadata
    """
    try:
        file_ext = Path(file_path).suffix.lower()

        # Determine target size
        size_map = {"thumbnail": (300, 300), "medium": (800, 800), "large": (1600, 1600), "full": None}
        target_size = size_map.get(size, (800, 800))

        # Handle FITS files
        if file_ext in [".fits", ".fit", ".fts"]:
            # Try memory mapping first, fall back to regular loading if needed
            hdul = None
            use_memmap = True

            try:
                hdul = fits.open(file_path, memmap=True)

                # Try to find image data in HDUs
                data = None
                for hdu in hdul:
                    try:
                        # Accessing hdu.data can trigger the memmap error
                        if hdu.data is not None and len(hdu.data.shape) >= 2:
                            data = hdu.data
                            break
                    except ValueError as e:
                        if "BZERO/BSCALE/BLANK" in str(e):
                            # Need to reload without memmap
                            use_memmap = False
                            break
                        raise

                # If we hit the memmap error, reload without memmap
                if not use_memmap:
                    hdul.close()
                    hdul = fits.open(file_path, memmap=False)
                    data = None
                    for hdu in hdul:
                        if hdu.data is not None and len(hdu.data.shape) >= 2:
                            data = hdu.data
                            break

            except (ValueError, OSError) as e:
                if "BZERO/BSCALE/BLANK" in str(e):
                    # If memmap fails at open time, load normally
                    print(f"Memory mapping failed at open, loading normally: {e}")
                    if hdul:
                        hdul.close()
                    hdul = fits.open(file_path, memmap=False)
                    data = None
                    for hdu in hdul:
                        if hdu.data is not None and len(hdu.data.shape) >= 2:
                            data = hdu.data
                            break
                else:
                    raise

            try:
                if data is None:
                    return {"error": "No image data in FITS file"}

                # Handle 3D data (take first slice if it's a cube)
                if len(data.shape) == 3:
                    if data.shape[0] == 3:
                        # RGB cube (3, H, W) - transpose to (H, W, 3)
                        data = np.transpose(data, (1, 2, 0))
                    elif data.shape[0] < data.shape[1] and data.shape[0] < data.shape[2]:
                        # Likely (N, H, W) - take first slice
                        data = data[0]
                    else:
                        # Take middle slice
                        data = data[data.shape[0] // 2]

                # Downsample large images before processing for speed
                # We only need enough pixels to satisfy the target size (e.g. 800x800 or 1600x1600)
                if target_size and (data.shape[0] > target_size[1] or data.shape[1] > target_size[0]):
                    # Calculate skip factor
                    skip_y = max(1, data.shape[0] // target_size[1])
                    skip_x = max(1, data.shape[1] // target_size[0])
                    skip = min(skip_y, skip_x)
                    if skip > 1:
                        if data.ndim == 2:
                            data = data[::skip, ::skip]
                        else:
                            data = data[::skip, ::skip, :]

                # Apply stretch
                if stretch == "mtf":
                    # Use MTF autostretch
                    stretch_settings = load_stretch_settings()
                    if target_size:
                        preview = generate_preview_mtf(
                            data,
                            size=target_size,
                            target_background=stretch_settings.get("target_background", 0.17),
                            shadows_clipping=stretch_settings.get("shadows_clipping", -2.8),
                            contrast_boost=stretch_settings.get("contrast_boost", 1.1),
                            linked_channels=stretch_settings.get("linked_channels", True),
                        )
                    else:
                        stretch_settings = load_stretch_settings()
                        use_linked = stretch_settings.get("linked_channels", True)
                        if use_linked:
                            stretched = auto_stretch_linked(
                                data,
                                target_background=stretch_settings.get("target_background", 0.17),
                                shadows_clipping=stretch_settings.get("shadows_clipping", -2.8),
                            )
                        else:
                            stretched = auto_stretch_unlinked(
                                data,
                                target_background=stretch_settings.get("target_background", 0.17),
                                shadows_clipping=stretch_settings.get("shadows_clipping", -2.8),
                            )
                        preview = (stretched * 255).clip(0, 255).astype("uint8")
                else:
                    # Use Z-scale (legacy)
                    if data.ndim == 2:
                        interval = ZScaleInterval()
                        vmin, vmax = interval.get_limits(data)
                        normalized = ((data - vmin) / (vmax - vmin) * 255).clip(0, 255).astype("uint8")
                        preview = normalized
                    else:
                        # RGB data
                        preview = np.zeros((*data.shape[:2], 3), dtype=np.uint8)
                        for i in range(min(3, data.shape[2])):
                            interval = ZScaleInterval()
                            vmin, vmax = interval.get_limits(data[:, :, i])
                            preview[:, :, i] = (
                                ((data[:, :, i] - vmin) / (vmax - vmin) * 255).clip(0, 255).astype("uint8")
                            )

                # Convert to PIL Image
                if preview.ndim == 2:
                    img = Image.fromarray(preview, mode="L")
                else:
                    img = Image.fromarray(preview, mode="RGB")

                # Resize if needed and not already done
                if target_size and stretch != "mtf":
                    img.thumbnail(target_size, Image.Resampling.LANCZOS)

                buffer = BytesIO()
                # Use JPEG with quality=95 for full size to preserve star profiles/noise details, and quality=90 for others
                q = 95 if size == "full" else 90
                img.save(buffer, format="JPEG", quality=q)
                img_bytes = buffer.getvalue()

                # Extract metadata for FITS files
                meta = extract_meta(file_path)

                result = {
                    "image_bytes": img_bytes,
                    "shape": data.shape,
                    "stretch": stretch,
                    "size": size,
                    "file_type": "fits",
                }

                # Add metadata fields if available
                if "object" in meta:
                    result["object"] = meta["object"]
                if "astrometry" in meta:
                    result["astrometry"] = meta["astrometry"]

                return result
            finally:
                if hdul:
                    hdul.close()

        # Handle image files (PNG, TIFF)
        elif file_ext in [".png", ".tif", ".tiff"]:
            img = Image.open(file_path)

            # Convert to RGB if needed
            if img.mode not in ["RGB", "L"]:
                img = img.convert("RGB")

            # Resize if needed
            if target_size:
                img.thumbnail(target_size, Image.Resampling.LANCZOS)

            buffer = BytesIO()
            # Use JPEG with quality=95 for full size to preserve details, and quality=90 for others
            q = 95 if size == "full" else 90
            img.save(buffer, format="JPEG", quality=q)
            img_bytes = buffer.getvalue()

            # Extract metadata for PNG/TIFF files
            meta = extract_meta_from_image(file_path)

            result = {
                "image_bytes": img_bytes,
                "shape": (img.height, img.width),
                "stretch": "none",
                "size": size,
                "file_type": file_ext.replace(".", ""),
            }

            # Add metadata fields if available
            if "object" in meta:
                result["object"] = meta["object"]
            if "astrometry" in meta:
                result["astrometry"] = meta["astrometry"]

            return result

        else:
            return {"error": f"Unsupported file type: {file_ext}"}

    except Exception as e:
        print(f"Error in get_fits_preview: {e}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}


def get_fits_preview_old(file_path):
    """Generate a base64-encoded preview image (legacy function)."""
    return get_fits_preview(file_path, size="medium", stretch="mtf")
