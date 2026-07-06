"""Folder scanning and catalog building."""

import asyncio
import time
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from .metadata_extractor import extract_meta, extract_meta_from_image
from .cross_reference import get_canonical_name
from .cache_manager import load_catalog_cache, save_catalog_cache, load_favorites, CATALOG_FILE
from .thumbnail_generator import generate_thumbnail
from .path_pattern import PathPattern, apply_ignore_filters


def update_file_metadata_in_cache(file_path: str):
    """
    Update a specific file's metadata in the cached catalog without rescanning.
    Also updates the group-level astrometry if this file has coordinates.

    Args:
        file_path: Path to the file that was updated

    Returns:
        True if successful, False otherwise
    """
    if not CATALOG_FILE.exists():
        print("[CACHE UPDATE] No catalog cache exists")
        return False

    try:
        # Load the cache
        import json

        with open(CATALOG_FILE, "r") as f:
            cache = json.load(f)

        print(f"[CACHE UPDATE] Updating metadata for: {file_path}")

        # Extract fresh metadata from the file
        file_ext = Path(file_path).suffix.lower()
        if file_ext in [".fits", ".fit", ".fts"]:
            fresh_meta = extract_meta(file_path)
        else:
            fresh_meta = extract_meta_from_image(file_path)

        if "error" in fresh_meta:
            print(f"[CACHE UPDATE] Error extracting metadata: {fresh_meta['error']}")
            return False

        print(
            f"[CACHE UPDATE] Fresh metadata: object={fresh_meta.get('object')}, astrometry={fresh_meta.get('astrometry')}"
        )

        # Find and update the file in the cache
        updated = False
        updated_group = None
        for group in cache.get("groups", []):
            for file_meta in group.get("files", []):
                if file_meta["path"] == file_path:
                    # Update the metadata
                    file_meta.update(fresh_meta)
                    updated = True
                    updated_group = group
                    print(f"[CACHE UPDATE] Updated file in group: {group.get('object')}")
                    break

            # Also check sessions if they exist
            if "sessions" in group:
                for session in group["sessions"]:
                    for file_meta in session.get("files", []):
                        if file_meta["path"] == file_path:
                            file_meta.update(fresh_meta)
                            updated = True
                            updated_group = group
                            print("[CACHE UPDATE] Updated file in session")
                            break

            if updated:
                break

        if updated and updated_group:
            # Update group-level astrometry if the file has coordinates
            if "astrometry" in fresh_meta and fresh_meta["astrometry"]:
                updated_group["astrometry"] = fresh_meta["astrometry"]
                print(f"[CACHE UPDATE] Updated group-level astrometry: {fresh_meta['astrometry']}")

            # Save the updated cache
            with open(CATALOG_FILE, "w") as f:
                json.dump(cache, f, indent=2)
            print(f"[CACHE UPDATE] Successfully updated cache for {Path(file_path).name}")
            return True
        else:
            print(f"[CACHE UPDATE] File not found in cache: {file_path}")
            return False

    except Exception as e:
        print(f"[CACHE UPDATE] Error updating file metadata in cache: {e}")
        import traceback

        traceback.print_exc()
        return False


async def scan_fits_folder(folder_path, use_cache=True, progress_callback=None, scan_pattern=None, ignore_filters=None):
    """Scan folder recursively for FITS and image files, group by object.

    Args:
        folder_path: Root folder to scan
        use_cache: Whether to use cached results
        progress_callback: Async callback for progress updates
        scan_pattern: Optional pattern string (e.g., '$TARGETNAME$/$DATE$')
        ignore_filters: Optional list of path substrings to ignore
    """
    scan_start_time = time.time()

    # Clean up the path
    folder_path = folder_path.replace("\\ ", " ")
    path = Path(folder_path)

    # Parse the scan pattern
    path_pattern = PathPattern(scan_pattern) if scan_pattern else None
    if path_pattern and not path_pattern.is_empty:
        print(f"[SCAN] Using scan pattern: {path_pattern.describe()}")
    else:
        path_pattern = None
        print("[SCAN] No scan pattern configured, using auto-detect")

    if ignore_filters:
        print(f"[SCAN] Ignore filters: {ignore_filters}")

    print(f"[SCAN] Starting scan of path: {path}")
    print(f"       Path exists: {path.exists()}")

    if not path.exists():
        return {"error": f"Path does not exist: {folder_path}", "count": 0, "groups": []}

    # Try to load from cache
    if use_cache:
        cached = load_catalog_cache(str(path))
        if cached:
            elapsed = time.time() - scan_start_time
            print(f"[PERF] Loaded from cache in {elapsed:.3f}s")
            if progress_callback:
                try:
                    await progress_callback(
                        {
                            "type": "progress",
                            "stage": "complete",
                            "message": "Loaded from cache",
                            "current": cached["count"],
                            "total": cached["count"],
                        }
                    )
                except Exception as e:
                    print(f"Error sending progress: {e}")
            return cached

    if progress_callback:
        try:
            await progress_callback(
                {"type": "progress", "stage": "scanning", "message": "Scanning for files...", "current": 0, "total": 0}
            )
        except Exception as e:
            print(f"Error sending progress: {e}")

    file_scan_start = time.time()
    all_files = []
    seen_files = set()  # Track files we've already added

    # Search for files with progress updates
    # Note: Use lowercase patterns only since Windows is case-insensitive
    extensions = {"fits": ["*.fits", "*.fit", "*.fts"], "image": ["*.png", "*.tif", "*.tiff"]}

    for file_type, exts in extensions.items():
        for ext in exts:
            for file_path in path.rglob(ext):
                # Normalize path to avoid duplicates on case-insensitive filesystems
                normalized_path = str(file_path).lower()
                if normalized_path not in seen_files:
                    seen_files.add(normalized_path)
                    all_files.append((file_path, file_type))

                # Send progress update every 50 files found
                if progress_callback and len(all_files) % 50 == 0:
                    try:
                        await progress_callback(
                            {
                                "type": "progress",
                                "stage": "scanning",
                                "message": f"Found {len(all_files)} files...",
                                "current": len(all_files),
                                "total": 0,
                                "current_file": str(file_path.name),
                            }
                        )
                        await asyncio.sleep(0)  # Allow event loop to process
                    except Exception as e:
                        print(f"Error sending progress: {e}")

    file_scan_elapsed = time.time() - file_scan_start
    total_before_filter = len(all_files)

    # Apply ignore filters
    if ignore_filters:
        all_files = apply_ignore_filters(all_files, ignore_filters)
        filtered_count = total_before_filter - len(all_files)
        if filtered_count > 0:
            print(f"[SCAN] Filtered out {filtered_count} files by ignore filters")

    print(f"[PERF] File scanning completed in {file_scan_elapsed:.3f}s")
    print(f"[PERF] Total files found: {len(all_files)} (before filter: {total_before_filter})")

    if progress_callback:
        try:
            await progress_callback(
                {
                    "type": "progress",
                    "stage": "processing",
                    "message": f"Processing {len(all_files)} files...",
                    "current": 0,
                    "total": len(all_files),
                }
            )
        except Exception as e:
            print(f"Error sending progress: {e}")

    # Extract metadata using thread pool to avoid blocking event loop
    metadata = []
    favorites = load_favorites()
    base_path = str(path)  # Store base path for relative path extraction

    meta_start = time.time()

    # Use ThreadPoolExecutor to run blocking file operations
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=8)  # Increased from 4 to 8

    for idx, (file_path, file_type) in enumerate(all_files):
        try:
            if file_type == "fits":
                meta = await loop.run_in_executor(executor, extract_meta, file_path, base_path, path_pattern)
            else:
                meta = await loop.run_in_executor(executor, extract_meta_from_image, file_path, base_path, path_pattern)

            if "error" not in meta:
                metadata.append(meta)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

        # Send progress update more frequently during processing
        if progress_callback and ((idx + 1) % 5 == 0 or idx == len(all_files) - 1):
            try:
                await progress_callback(
                    {
                        "type": "progress",
                        "stage": "processing",
                        "message": f"Processing: {Path(file_path).name}",
                        "current": idx + 1,
                        "total": len(all_files),
                        "current_file": str(file_path),
                    }
                )
                await asyncio.sleep(0)  # Allow event loop to process other tasks
            except Exception as e:
                print(f"Error sending progress: {e}")

    executor.shutdown(wait=False)

    meta_elapsed = time.time() - meta_start
    print(
        f"[PERF] Metadata extraction completed in {meta_elapsed:.3f}s ({meta_elapsed / len(all_files) * 1000:.1f}ms per file)"
    )

    if progress_callback:
        try:
            await progress_callback(
                {
                    "type": "progress",
                    "stage": "grouping",
                    "message": "Grouping by objects...",
                    "current": len(metadata),
                    "total": len(all_files),
                }
            )
        except Exception as e:
            print(f"Error sending progress: {e}")

    # Group by canonical object name (cross-referencing M/NGC/C)
    group_start = time.time()
    groups = defaultdict(list)
    for idx, meta in enumerate(metadata):
        obj_name = meta["object"]
        canonical_name = get_canonical_name(obj_name)
        meta["canonical_name"] = canonical_name
        groups[canonical_name].append(meta)

    group_elapsed = time.time() - group_start
    print(f"[PERF] Grouping completed in {group_elapsed:.3f}s ({len(groups)} unique objects)")

    # Prepare thumbnail generation tasks
    thumbnail_start = time.time()
    thumbnail_tasks = []

    # Convert to list format with session grouping
    grouped_list = []
    for obj_name, files in groups.items():
        # Check if files come from multiple sessions
        sessions = defaultdict(list)
        for f in files:
            session_date = f.get("session_date", "Unknown")
            sessions[session_date].append(f)

        # Get favorite file for this object
        favorite_path = favorites.get(obj_name)

        # If multiple sessions, create sub-groups
        if len(sessions) > 1:
            # Create a parent group with all files
            all_files_sorted = sorted(files, key=lambda x: x.get("session_date", "Unknown"))

            # Find preview file: favorite > processed image > first file
            preview_file = None
            if favorite_path:
                for f in all_files_sorted:
                    if f["path"] == favorite_path:
                        preview_file = f
                        break

            if not preview_file:
                for f in all_files_sorted:
                    if f["file_type"] in ["png", "tiff", "tif"]:
                        preview_file = f
                        break

            if not preview_file and all_files_sorted:
                preview_file = all_files_sorted[0]

            # Queue thumbnail generation (don't wait for it)
            preview_path = preview_file["path"] if preview_file else None
            thumbnail_tasks.append((obj_name, preview_path, "main"))

            # Create session sub-groups
            session_groups = []
            for session_date in sorted(sessions.keys()):
                session_files = sessions[session_date]

                # Find preview for this session
                session_preview = None
                for f in session_files:
                    if f["file_type"] in ["png", "tiff", "tif"]:
                        session_preview = f
                        break
                if not session_preview and session_files:
                    session_preview = session_files[0]

                # Queue session thumbnail
                session_preview_path = session_preview["path"] if session_preview else None
                thumbnail_tasks.append((obj_name, session_preview_path, f"session_{session_date}"))

                session_groups.append(
                    {
                        "session_date": session_date,
                        "count": len(session_files),
                        "files": session_files,
                        "preview": session_preview_path,
                        "thumbnail": None,  # Will be generated async
                    }
                )

            grouped_list.append(
                {
                    "object": obj_name,
                    "count": len(files),
                    "files": all_files_sorted,
                    "preview": preview_path,
                    "thumbnail": None,  # Will be generated async
                    "session_date": "Multiple",
                    "sessions": session_groups,
                    "favorite": favorite_path,
                }
            )
        else:
            # Single session, create simple group
            session_date = list(sessions.keys())[0]
            session_files = sessions[session_date]

            # Find preview file: favorite > processed image > first file
            preview_file = None
            if favorite_path:
                for f in session_files:
                    if f["path"] == favorite_path:
                        preview_file = f
                        break

            if not preview_file:
                for f in session_files:
                    if f["file_type"] in ["png", "tiff", "tif"]:
                        preview_file = f
                        break

            if not preview_file and session_files:
                preview_file = session_files[0]

            # Queue thumbnail generation
            preview_path = preview_file["path"] if preview_file else None
            thumbnail_tasks.append((obj_name, preview_path, "main"))

            grouped_list.append(
                {
                    "object": obj_name,
                    "count": len(session_files),
                    "files": session_files,
                    "preview": preview_path,
                    "thumbnail": None,  # Will be generated async
                    "session_date": session_date,
                    "favorite": favorite_path,
                }
            )

    # Enrich groups with astrometry data (only once per object, not per file)
    print(f"[PERF] Enriching {len(grouped_list)} objects with astrometry data...")
    enrich_start = time.time()

    for group in grouped_list:
        # Special debug logging for NGC0896
        is_ngc896 = "NGC0896" in group["object"] or "NGC896" in group["object"]

        # Find the first file with COMPLETE astrometry data (must have ra AND dec)
        astrometry = None
        for file_meta in group["files"]:
            if "astrometry" in file_meta and file_meta["astrometry"]:
                astro_data = file_meta["astrometry"]
                # Only use astrometry if it has both ra and dec coordinates
                if (
                    "ra" in astro_data
                    and "dec" in astro_data
                    and astro_data["ra"] is not None
                    and astro_data["dec"] is not None
                ):
                    astrometry = astro_data
                    if is_ngc896:
                        print(f"[NGC0896 DEBUG] [OK] Found coordinates in file: {file_meta.get('filename', 'unknown')}")
                        print(f"[NGC0896 DEBUG]   ra={astrometry.get('ra')}, dec={astrometry.get('dec')}")
                    break

        # If no file has coordinates, try to get them from catalog
        if not astrometry:
            if is_ngc896:
                print(f"[NGC0896 DEBUG] No file coordinates, trying catalog lookup for {group['object']}...")

            from .astro_info import get_object_info

            obj_info = get_object_info(group["object"])
            if obj_info and "ra" in obj_info and "dec" in obj_info:
                # Create minimal astrometry from catalog coordinates
                astrometry = {"ra": obj_info["ra"], "dec": obj_info["dec"]}
                if is_ngc896:
                    print(
                        f"[NGC0896 DEBUG] [OK] Got coordinates from catalog: ra={astrometry['ra']}, dec={astrometry['dec']}"
                    )
            elif is_ngc896:
                print("[NGC0896 DEBUG] [FAIL] Catalog lookup returned no coordinates")

        # Add astrometry to group level if found
        if astrometry:
            group["astrometry"] = astrometry
        elif is_ngc896:
            print(f"[NGC0896 DEBUG] [FAIL] No astrometry available for {group['object']}")

    enrich_elapsed = time.time() - enrich_start
    print(f"[PERF] Astrometry enrichment completed in {enrich_elapsed:.3f}s")

    # Generate thumbnails in parallel using ThreadPoolExecutor
    print(f"[PERF] Generating {len(thumbnail_tasks)} thumbnails in parallel...")
    executor = ThreadPoolExecutor(max_workers=8)  # Increased from 4 to 8
    thumbnail_futures = []

    for obj_name, preview_path, thumb_type in thumbnail_tasks:
        if preview_path:
            future = loop.run_in_executor(executor, generate_thumbnail, preview_path)
            thumbnail_futures.append((obj_name, thumb_type, future))

    # Wait for all thumbnails to complete
    thumbnail_results = {}
    for obj_name, thumb_type, future in thumbnail_futures:
        try:
            thumb_path = await future
            key = f"{obj_name}_{thumb_type}"
            thumbnail_results[key] = thumb_path
        except Exception as e:
            print(f"Error generating thumbnail for {obj_name}: {e}")

    executor.shutdown(wait=False)

    # Update groups with generated thumbnails
    for group in grouped_list:
        main_key = f"{group['object']}_main"
        if main_key in thumbnail_results:
            group["thumbnail"] = thumbnail_results[main_key]

        # Update session thumbnails if present
        if "sessions" in group:
            for session in group["sessions"]:
                session_key = f"{group['object']}_session_{session['session_date']}"
                if session_key in thumbnail_results:
                    session["thumbnail"] = thumbnail_results[session_key]

    thumbnail_elapsed = time.time() - thumbnail_start
    print(f"[PERF] Thumbnail generation completed in {thumbnail_elapsed:.3f}s")

    # Sort by object name
    grouped_list.sort(key=lambda x: x["object"])

    result = {"count": len(metadata), "groups": grouped_list}

    # Debug: Check NGC0896 in final result before caching
    for group in grouped_list:
        if "NGC0896" in group["object"] or "NGC896" in group["object"]:
            print(f"[NGC0896 DEBUG] Final result before cache - {group['object']}:")
            print(f"[NGC0896 DEBUG]   Has astrometry: {'astrometry' in group}")
            if "astrometry" in group:
                print(f"[NGC0896 DEBUG]   Astrometry: {group['astrometry']}")

    # Save to cache
    save_catalog_cache(str(path), result)

    total_elapsed = time.time() - scan_start_time
    print("[PERF] ========== SCAN SUMMARY ==========")
    print(f"[PERF] Total time: {total_elapsed:.3f}s")
    print(f"[PERF] Files found: {len(all_files)}")
    print(f"[PERF] Objects grouped: {len(grouped_list)}")
    print(f"[PERF] File scanning: {file_scan_elapsed:.3f}s")
    print(f"[PERF] Metadata extraction: {meta_elapsed:.3f}s ({meta_elapsed / len(all_files) * 1000:.1f}ms/file)")
    print(f"[PERF] Grouping: {group_elapsed:.3f}s")
    print(f"[PERF] Thumbnails: {thumbnail_elapsed:.3f}s")
    print("[PERF] ====================================")

    if progress_callback:
        await progress_callback(
            {
                "type": "progress",
                "stage": "complete",
                "message": f"Scan complete! Found {len(grouped_list)} objects",
                "current": len(all_files),
                "total": len(all_files),
            }
        )

    return result
