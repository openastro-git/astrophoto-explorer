"""Cache management for catalog and favorites."""

from pathlib import Path
import json
from datetime import datetime

CACHE_DIR = Path(".cache")
THUMBS_DIR = CACHE_DIR / "thumbs"
CATALOG_FILE = CACHE_DIR / "catalog.json"
FAVORITES_FILE = CACHE_DIR / "favorites.json"


def ensure_cache_dirs():
    """Ensure cache directories exist."""
    CACHE_DIR.mkdir(exist_ok=True)
    THUMBS_DIR.mkdir(exist_ok=True)


def load_favorites():
    """Load favorites from cache."""
    if FAVORITES_FILE.exists():
        try:
            with open(FAVORITES_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_favorites(favorites):
    """Save favorites to cache."""
    ensure_cache_dirs()
    try:
        with open(FAVORITES_FILE, "w") as f:
            json.dump(favorites, f, indent=2)
    except Exception as e:
        print(f"Error saving favorites: {e}")


def set_favorite_image(object_name, file_path):
    """Set a file as favorite for an object."""
    favorites = load_favorites()
    favorites[object_name] = file_path
    save_favorites(favorites)
    return True


def get_favorite_image(object_name):
    """Get the favorite file for an object."""
    favorites = load_favorites()
    return favorites.get(object_name)


def load_catalog_cache(folder_path):
    """Load cached catalog if it exists and is valid."""
    if not CATALOG_FILE.exists():
        return None

    try:
        with open(CATALOG_FILE, "r") as f:
            cache = json.load(f)

        # Check if cache is for the same folder
        if cache.get("folder_path") == folder_path:
            # Verify files still exist
            all_valid = True
            for group in cache.get("groups", []):
                for file_meta in group.get("files", []):
                    if not Path(file_meta["path"]).exists():
                        all_valid = False
                        break
                if not all_valid:
                    break

            if all_valid:
                print("Using cached catalog")

                # Debug: Check NGC0896 metadata in cache
                for group in cache.get("groups", []):
                    if "NGC0896" in group.get("object", "") or "NGC896" in group.get("object", ""):
                        print(f"[NGC0896 CACHE LOAD DEBUG] {group['object']} group found in cache")
                        print(f"[NGC0896 CACHE LOAD DEBUG]   Has group-level astrometry: {'astrometry' in group}")
                        if "astrometry" in group:
                            print(f"[NGC0896 CACHE LOAD DEBUG]   Group astrometry: {group['astrometry']}")

                        # Check files too
                        for file_meta in group.get("files", []):
                            if "astrometry" in file_meta:
                                print(
                                    f"[NGC0896 CACHE LOAD DEBUG]   File {file_meta.get('filename', 'unknown')} has astrometry: {file_meta['astrometry']}"
                                )
                                break
                        break

                return cache

    except Exception as e:
        print(f"Error loading cache: {e}")

    return None


def save_catalog_cache(folder_path, catalog_data):
    """Save catalog to cache."""
    ensure_cache_dirs()

    try:
        cache = {
            "folder_path": folder_path,
            "timestamp": datetime.now().isoformat(),
            "groups": catalog_data["groups"],
            "count": catalog_data["count"],
        }

        # Debug: Check NGC0896 before writing to cache
        for group in cache["groups"]:
            if "NGC0896" in group["object"] or "NGC896" in group["object"]:
                print(f"[NGC0896 CACHE SAVE DEBUG] Saving {group['object']} to cache:")
                print(f"[NGC0896 CACHE SAVE DEBUG]   Has astrometry: {'astrometry' in group}")
                if "astrometry" in group:
                    print(f"[NGC0896 CACHE SAVE DEBUG]   Astrometry: {group['astrometry']}")

        with open(CATALOG_FILE, "w") as f:
            json.dump(cache, f, indent=2)

        print("Catalog cached successfully")
    except Exception as e:
        print(f"Error saving cache: {e}")


def invalidate_catalog_cache():
    """Invalidate (delete) the catalog cache to force a rescan."""
    try:
        if CATALOG_FILE.exists():
            CATALOG_FILE.unlink()
            print("Catalog cache invalidated")
            return True
    except Exception as e:
        print(f"Error invalidating catalog cache: {e}")
    return False


def update_catalog_favorite(object_name, file_path, thumbnail_path):
    """Update cached catalog with new favorite and thumbnail for an object."""
    if not CATALOG_FILE.exists():
        return False

    try:
        with open(CATALOG_FILE, "r") as f:
            cache = json.load(f)

        # Find and update the group with matching object name
        for group in cache.get("groups", []):
            if group.get("object") == object_name:
                group["favorite"] = file_path
                group["thumbnail"] = thumbnail_path

                # Also update sessions if they exist
                if "sessions" in group:
                    for session in group["sessions"]:
                        # Find the favorite file in this session
                        for file_meta in session.get("files", []):
                            if file_meta["path"] == file_path:
                                session["preview"] = file_path
                                session["thumbnail"] = thumbnail_path
                                break

                break

        # Save the updated cache
        with open(CATALOG_FILE, "w") as f:
            json.dump(cache, f, indent=2)

        print(f"Updated catalog favorite for {object_name}")
        return True
    except Exception as e:
        print(f"Error updating catalog favorite: {e}")
        return False
