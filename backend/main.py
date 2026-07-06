from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from .scanner import scan_fits_folder, update_file_metadata_in_cache
from .image_preview import get_fits_preview, get_image_info
from .cache_manager import set_favorite_image, get_favorite_image, update_catalog_favorite, CACHE_DIR, FAVORITES_FILE
from .thumbnail_generator import generate_thumbnail
from .websocket_manager import manager
from .path_pattern import PathPattern, apply_ignore_filters, get_available_variables
from pydantic import BaseModel
import json
import shutil
import asyncio
import sys
import queue

# Log capturing redirection for streaming stdout/stderr to the frontend console
log_queue = queue.Queue()
log_connections = set()


class LogCaptureStream:
    def __init__(self, original_stream, log_queue):
        self.original_stream = original_stream
        self.log_queue = log_queue

    def write(self, text):
        if self.original_stream is not None:
            try:
                self.original_stream.write(text)
                self.original_stream.flush()
            except Exception:
                pass
        if text:
            # Prevent infinite feedback loop for log WebSocket messages
            if "/ws/logs" in text or "GET /ws/logs" in text:
                return
            self.log_queue.put(text)

    def flush(self):
        if self.original_stream is not None:
            try:
                self.original_stream.flush()
            except Exception:
                pass


# Redirect stdout and stderr
sys.stdout = LogCaptureStream(sys.stdout, log_queue)
sys.stderr = LogCaptureStream(sys.stderr, log_queue)


async def log_broadcaster():
    """Background task to pull logs from the queue and send them over WebSockets."""
    while True:
        try:
            while not log_queue.empty():
                log_text = log_queue.get_nowait()
                if log_connections:
                    disconnected = set()
                    for websocket in log_connections:
                        try:
                            await websocket.send_json({"type": "log", "message": log_text})
                        except Exception:
                            disconnected.add(websocket)
                    for ws in disconnected:
                        log_connections.discard(ws)
        except Exception:
            pass
        await asyncio.sleep(0.05)


app = FastAPI()


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(log_broadcaster())


# Enable CORS for Vite dev server and standalone mode
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Image-Shape",
        "X-Image-Stretch",
        "X-Image-Size",
        "X-Image-FileType",
        "X-Image-Object",
        "X-Image-Astrometry",
    ],
)

# Mount static files for standalone mode (if ui directory exists)
UI_DIR = Path("ui")
if UI_DIR.exists() and UI_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=UI_DIR / "assets"), name="assets")

    @app.get("/")
    def serve_ui():
        """Serve the UI in standalone mode."""
        index_file = UI_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"status": "Astrophoto Explorer API"}
else:

    @app.get("/")
    def root():
        return {"status": "Astrophoto Explorer API"}


CONFIG_FILE = Path("config.json")


class StretchSettings(BaseModel):
    target_background: float = 0.17
    shadows_clipping: float = -2.8
    contrast_boost: float = 1.1
    linked_channels: bool = True


class Settings(BaseModel):
    default_folder: str
    default_render: str = "HD"
    scan_pattern: str = ""
    ignore_filters: list = []
    stretch: StretchSettings = StretchSettings()
    theme: str = "deep-space"


@app.get("/api/settings")
def get_settings():
    """Get current settings from config file."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            # Ensure stretch settings have defaults
            if "stretch" not in config:
                config["stretch"] = {
                    "target_background": 0.17,
                    "shadows_clipping": -2.8,
                    "contrast_boost": 1.1,
                    "linked_channels": True,
                }
            if "default_render" not in config:
                config["default_render"] = "HD"
            if "scan_pattern" not in config:
                config["scan_pattern"] = ""
            if "ignore_filters" not in config:
                config["ignore_filters"] = []
            if "theme" not in config:
                config["theme"] = "deep-space"
            return config
    return {
        "default_folder": ".",
        "default_render": "HD",
        "scan_pattern": "",
        "ignore_filters": [],
        "stretch": {
            "target_background": 0.17,
            "shadows_clipping": -2.8,
            "contrast_boost": 1.1,
            "linked_channels": True,
        },
        "theme": "deep-space",
    }


@app.post("/api/settings")
def save_settings(settings: Settings):
    """Save settings to config file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(settings.dict(), f, indent=2)
    return {"status": "saved", "settings": settings}


@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint for streaming system log outputs to the frontend console."""
    await websocket.accept()
    log_connections.add(websocket)
    try:
        while True:
            # Keep WebSocket connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        log_connections.discard(websocket)


@app.websocket("/ws/scan")
async def websocket_scan(websocket: WebSocket):
    """WebSocket endpoint for real-time scan progress."""
    print("[WS] WebSocket connection attempt")
    await manager.connect(websocket)
    print("[WS] WebSocket connected")

    try:
        # Wait for scan request
        print("[WS] Waiting for scan request...")
        data = await websocket.receive_json()
        print(f"[WS] Received scan request: {data}")

        path = data.get("path", ".")
        force = data.get("force", False)

        # Load scan pattern and ignore filters from config
        scan_pattern = None
        ignore_filters = None
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    scan_pattern = config.get("scan_pattern", "") or None
                    ignore_filters = config.get("ignore_filters", []) or None
            except Exception as e:
                print(f"[WS] Error reading config for pattern/filters: {e}")

        print(f"[WS] Starting scan: path={path}, force={force}, pattern={scan_pattern}, filters={ignore_filters}")

        # Run scan with progress updates
        result = await scan_fits_folder(
            path,
            use_cache=not force,
            progress_callback=manager.send_progress,
            scan_pattern=scan_pattern,
            ignore_filters=ignore_filters,
        )

        print(
            f"[WS] Scan complete, sending result with {result.get('count', 0)} files, {len(result.get('groups', []))} groups"
        )

        # Send final result
        await websocket.send_json({"type": "complete", "data": result})

        print("[WS] Result sent successfully")

    except WebSocketDisconnect:
        print("[WS] WebSocket disconnected by client")
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[WS] WebSocket error: {e}")
        import traceback

        traceback.print_exc()
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
        manager.disconnect(websocket)
    finally:
        # Always close the connection when done
        manager.disconnect(websocket)
        try:
            await websocket.close()
        except:
            pass


@app.get("/api/scan")
async def scan_folder(path: str = ".", force: bool = False):
    """Scan a folder for FITS files and return metadata (legacy endpoint)."""
    # Load pattern/filters from config
    scan_pattern = None
    ignore_filters = None
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                scan_pattern = config.get("scan_pattern", "") or None
                ignore_filters = config.get("ignore_filters", []) or None
        except Exception:
            pass
    return await scan_fits_folder(path, use_cache=not force, scan_pattern=scan_pattern, ignore_filters=ignore_filters)


@app.get("/api/scan/variables")
def get_pattern_variables():
    """Get list of available pattern variables for the UI."""
    return {"variables": get_available_variables()}


@app.post("/api/scan/test-pattern")
async def test_scan_pattern(data: dict):
    """Test a scan pattern against a few files without full scan.

    Expects: { path, pattern, ignore_filters, limit }
    Returns a preview of detected metadata for up to `limit` files.
    """
    from .metadata_extractor import extract_meta, extract_meta_from_image

    folder_path = data.get("path", ".")
    pattern_str = data.get("pattern", "")
    ignore_filters = data.get("ignore_filters", [])
    limit = min(data.get("limit", 5), 20)  # Cap at 20

    folder_path = folder_path.replace("\\ ", " ")
    path = Path(folder_path)

    if not path.exists():
        return {"error": f"Path does not exist: {folder_path}", "results": []}

    # Parse the pattern
    path_pattern = PathPattern(pattern_str) if pattern_str else None

    # Find files (limited)
    extensions = {"fits": ["*.fits", "*.fit", "*.fts"], "image": ["*.png", "*.tif", "*.tiff"]}

    all_files = []
    seen_files = set()
    for file_type, exts in extensions.items():
        for ext in exts:
            for file_path_found in path.rglob(ext):
                normalized_path = str(file_path_found).lower()
                if normalized_path not in seen_files:
                    seen_files.add(normalized_path)
                    all_files.append((file_path_found, file_type))
                if len(all_files) >= limit * 3:  # Gather more to have some after filtering
                    break
            if len(all_files) >= limit * 3:
                break
        if len(all_files) >= limit * 3:
            break

    # Apply ignore filters
    if ignore_filters:
        all_files = apply_ignore_filters(all_files, ignore_filters)

    # Limit results
    all_files = all_files[:limit]

    # Extract metadata for each
    base_path = str(path)
    results = []
    for file_path_found, file_type in all_files:
        try:
            if file_type == "fits":
                meta = extract_meta(file_path_found, base_path, path_pattern)
            else:
                meta = extract_meta_from_image(file_path_found, base_path, path_pattern)

            if "error" not in meta:
                # Get relative path for display
                rel_path = str(file_path_found)
                if rel_path.lower().startswith(base_path.lower()):
                    rel_path = rel_path[len(base_path) :].lstrip("/\\\\")

                results.append(
                    {
                        "relative_path": rel_path,
                        "object": meta.get("object", "Unknown"),
                        "session_date": meta.get("session_date"),
                        "filter": meta.get("filter", "N/A"),
                        "file_type": meta.get("file_type"),
                        "instrument": meta.get("instrument", "N/A"),
                        "exptime": meta.get("exptime", 0),
                        "extraction_source": meta.get("_extraction_source", "auto"),
                        "has_astrometry": "astrometry" in meta,
                    }
                )
        except Exception as e:
            results.append({"relative_path": str(file_path_found), "error": str(e)})

    return {
        "pattern": pattern_str,
        "pattern_description": path_pattern.describe() if path_pattern else "Auto-detect",
        "total_files_found": len(all_files),
        "results": results,
    }


@app.get("/api/thumbnail/{file_path:path}")
def get_thumbnail(file_path: str):
    """Serve a cached thumbnail image."""
    thumb_path = Path(file_path)
    if thumb_path.exists() and thumb_path.is_file():
        return FileResponse(thumb_path, media_type="image/jpeg")
    return {"error": "Thumbnail not found"}


@app.get("/api/preview/{file_path:path}")
def preview_image(file_path: str, size: str = "medium", stretch: str = "mtf"):
    """
    Generate a preview of a FITS file or serve image file.

    Args:
        file_path: Path to the file
        size: "thumbnail", "medium", "large", or "full"
        stretch: "zscale" or "mtf" (default)
    """
    print(f"[PREVIEW API] Called for file: {file_path}, size: {size}, stretch: {stretch}")
    data = get_fits_preview(file_path, size=size, stretch=stretch)

    if "error" in data:
        print(f"[PREVIEW API] Error generating preview: {data['error']}")
        return JSONResponse(content=data, status_code=400)

    image_bytes = data.get("image_bytes", b"")
    print(f"[PREVIEW API] Returned raw bytes size: {len(image_bytes)} bytes")
    if "astrometry" in data:
        print(f"[PREVIEW API] Astrometry data: {data['astrometry']}")
    else:
        print("[PREVIEW API] No astrometry data in response")

    # Set custom headers for metadata
    headers = {
        "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
        "ETag": f'"{hash((file_path, size, stretch))}"',
        "X-Image-Shape": json.dumps(data.get("shape", [])),
        "X-Image-Stretch": str(data.get("stretch", stretch)),
        "X-Image-Size": str(data.get("size", size)),
        "X-Image-FileType": str(data.get("file_type", "")),
    }

    if "object" in data:
        headers["X-Image-Object"] = str(data["object"])
    if "astrometry" in data:
        headers["X-Image-Astrometry"] = json.dumps(data["astrometry"])

    return Response(content=image_bytes, media_type="image/jpeg", headers=headers)


@app.get("/api/image/info/{file_path:path}")
def get_image_info_endpoint(file_path: str):
    """Get image dimensions and metadata without loading full data."""
    return get_image_info(file_path)


@app.get("/api/file/{file_path:path}")
def serve_file(file_path: str):
    """Serve the actual file (for images that can be displayed directly)."""
    file = Path(file_path)
    if not file.exists() or not file.is_file():
        return {"error": "File not found"}

    # Determine media type
    ext = file.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
        ".fits": "application/fits",
        ".fit": "application/fits",
        ".fts": "application/fits",
    }

    media_type = media_types.get(ext, "application/octet-stream")
    return FileResponse(file, media_type=media_type)


@app.delete("/api/cache")
def clear_cache():
    """Clear the catalog cache and thumbnails, but preserve favorites."""
    import json

    try:
        # Save favorites before clearing
        favorites_data = None
        if FAVORITES_FILE.exists():
            with open(FAVORITES_FILE, "r") as f:
                favorites_data = json.load(f)

        # Clear cache directory
        if CACHE_DIR.exists():
            shutil.rmtree(CACHE_DIR)

        # Restore favorites
        if favorites_data:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(FAVORITES_FILE, "w") as f:
                json.dump(favorites_data, f, indent=2)

        return {"status": "Cache cleared successfully (favorites preserved)"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/object/info/{object_name}")
def get_object_info_endpoint(object_name: str):
    """Get astronomical object information."""
    from .astro_info import get_object_info

    info = get_object_info(object_name)
    if info:
        return info
    return {"error": "Object information not found", "object": object_name}


@app.get("/api/fits/header/{file_path:path}")
def get_fits_header(file_path: str):
    """Get all FITS header data for a file."""
    from astropy.io import fits

    try:
        with fits.open(file_path) as hdul:
            # Get the primary HDU header
            header = hdul[0].header

            # Convert header to dictionary
            header_dict = {}
            for key in header.keys():
                try:
                    value = header[key]
                    # Convert to string for JSON serialization
                    header_dict[key] = str(value) if value is not None else "N/A"
                except:
                    header_dict[key] = "N/A"

            return header_dict
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/favorite")
def set_favorite(data: dict):
    """Set a file as favorite for an object."""
    object_name = data.get("object_name")
    file_path = data.get("file_path")

    if not object_name or not file_path:
        return {"error": "Missing object_name or file_path"}

    # Save favorite to favorites.json
    success = set_favorite_image(object_name, file_path)

    if success:
        # Generate thumbnail for the favorite file
        thumbnail_path = generate_thumbnail(file_path)

        # Update the cached catalog with the new favorite and thumbnail
        update_catalog_favorite(object_name, file_path, thumbnail_path)

    return {"success": success, "object": object_name, "file": file_path}


@app.post("/api/thumbnail/regenerate")
def regenerate_thumbnail(data: dict):
    """Regenerate thumbnail for a specific file."""
    object_name = data.get("object_name")
    file_path = data.get("file_path")

    if not object_name or not file_path:
        return {"error": "Missing object_name or file_path"}

    # Delete old thumbnail if exists
    # (generate_thumbnail will create new one with new hash)
    thumb_path = generate_thumbnail(file_path)

    # Update the cached catalog with the new thumbnail
    update_catalog_favorite(object_name, file_path, thumb_path)

    return {"success": True, "thumbnail": thumb_path, "object": object_name}


@app.get("/api/favorite/{object_name}")
def get_favorite(object_name: str):
    """Get the favorite file for an object."""
    favorite = get_favorite_image(object_name)
    if favorite:
        return {"favorite": favorite}
    return {"favorite": None}


@app.post("/api/metadata/save")
def save_metadata_endpoint(data: dict):
    """Save detected metadata to a file."""
    from .metadata_writer import save_metadata
    from .astro_info import get_object_info

    file_path = data.get("file_path")
    object_name = data.get("object_name")

    if not file_path or not object_name:
        return {"error": "Missing file_path or object_name"}

    # Get object info from catalogs
    obj_info = get_object_info(object_name)

    if not obj_info:
        return {"error": f"Could not find information for {object_name}"}

    # Extract coordinates from catalog
    metadata = {"object_name": object_name}

    # Parse RA and Dec from catalog format
    if "ra" in obj_info:
        ra_str = obj_info["ra"]
        metadata["ra_hms"] = ra_str
        print(f"[METADATA SAVE] Parsing RA: {ra_str}")
        # Convert HMS to degrees
        try:
            # Format: "05h34m31.9s" or "08h40. 4m" or "08h40.4m"
            import re

            # Remove spaces and normalize format
            ra_normalized = ra_str.replace(" ", "")
            # Try with seconds
            match = re.match(r"(\d+)h\s*(\d+)\.?\s*(\d+)m\s*([\d.]+)s?", ra_normalized)
            if match:
                hours, minutes_tens, minutes_ones, seconds = match.groups()
                minutes = float(f"{minutes_tens}.{minutes_ones}")
                hours = float(hours)
                seconds = float(seconds)
                ra_deg = (hours + minutes / 60 + seconds / 3600) * 15
                metadata["ra"] = ra_deg
                print(f"[METADATA SAVE] Parsed RA to degrees (with seconds): {ra_deg}")
            else:
                # Try without seconds: "08h40.4m" or "08h40m"
                match = re.match(r"(\d+)h\s*([\d.]+)m", ra_normalized)
                if match:
                    hours, minutes = match.groups()
                    hours = float(hours)
                    minutes = float(minutes)
                    ra_deg = (hours + minutes / 60) * 15
                    metadata["ra"] = ra_deg
                    print(f"[METADATA SAVE] Parsed RA to degrees (no seconds): {ra_deg}")
                else:
                    print(f"[METADATA SAVE] Failed to match RA regex for: {ra_str}")
        except Exception as e:
            print(f"Error parsing RA: {e}")
            import traceback

            traceback.print_exc()

    if "dec" in obj_info:
        dec_str = obj_info["dec"]
        metadata["dec_dms"] = dec_str
        print(f"[METADATA SAVE] Parsing DEC: {dec_str}")
        # Convert DMS to degrees
        try:
            # Format: "+22° 00′ 52.2″" or "-26° 31′ 32.7″" or "−03° 14′ 45. 3″" or "+19° 59′" (no seconds)
            import re

            # Handle both regular minus (-) and Unicode minus (−)
            dec_str_normalized = dec_str.replace("−", "-")
            # Try with seconds first
            match = re.match(r"([+-]?)(\d+)°\s*(\d+)′\s*([\d.]+)″?", dec_str_normalized)
            if match:
                sign_str, degrees, minutes, seconds = match.groups()
                sign = -1 if sign_str == "-" else 1
                dec_deg = sign * (float(degrees) + float(minutes) / 60 + float(seconds) / 3600)
                metadata["dec"] = dec_deg
                print(f"[METADATA SAVE] Parsed DEC to degrees: {dec_deg}")
            else:
                # Try without seconds (format: "+19° 59′")
                match = re.match(r"([+-]?)(\d+)°\s*(\d+)′?", dec_str_normalized)
                if match:
                    sign_str, degrees, minutes = match.groups()
                    sign = -1 if sign_str == "-" else 1
                    dec_deg = sign * (float(degrees) + float(minutes) / 60)
                    metadata["dec"] = dec_deg
                    print(f"[METADATA SAVE] Parsed DEC to degrees (no seconds): {dec_deg}")
                else:
                    print(f"[METADATA SAVE] Failed to match DEC regex for: {dec_str}")
        except Exception as e:
            print(f"Error parsing Dec: {e}")
            import traceback

            traceback.print_exc()

    # Save metadata to file
    success = save_metadata(file_path, metadata)

    if success:
        # Update the cached catalog with the new metadata
        print(f"[METADATA SAVE] Updating catalog cache for {file_path}")
        update_file_metadata_in_cache(file_path)

        return {"success": True, "file_path": file_path, "metadata": metadata, "object_info": obj_info}
    else:
        return {"error": "Failed to save metadata to file"}
