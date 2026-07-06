"""
Astronomical object information retrieval and caching.
Uses PyONGC for NGC/IC objects, a simple Messier catalog, and web search as fallback.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

# PyONGC will be loaded lazily to avoid startup CPU overhead
_ongc_cache = None

# Cache directory
CACHE_DIR = Path(".cache/astro_info")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _get_ongc():
    """Lazy-load PyONGC only when needed."""
    global _ongc_cache
    if _ongc_cache is None:
        try:
            import sys
            import pyongc
            from pyongc import ongc

            # When running as a PyInstaller bundle, patch DBPATH on both the package
            # and the ongc module (which imports it as a local name at load time)
            if getattr(sys, "frozen", False):
                _db_path = os.path.join(sys._MEIPASS, "pyongc", "ongc.db")
                if os.path.exists(_db_path):
                    pyongc.DBPATH = _db_path
                    ongc.DBPATH = _db_path
            _ongc_cache = ongc
        except ImportError:
            _ongc_cache = False  # Mark as unavailable
    return _ongc_cache if _ongc_cache else None


def _unload_ongc():
    """Unload PyONGC from memory after use to free resources."""
    global _ongc_cache
    _ongc_cache = None


def _save_to_catalog(catalog_name: str, obj_key: str, obj_data: dict) -> bool:
    """Save a newly discovered object to the local catalog file."""
    try:
        data_dir = Path(__file__).parent / "data"
        catalog_file = data_dir / f"{catalog_name}.json"

        # Load existing catalog
        if catalog_file.exists():
            with open(catalog_file, "r", encoding="utf-8") as f:
                catalog = json.load(f)
        else:
            catalog = {}

        # Add or update the object
        catalog[obj_key] = obj_data

        # Save back to file
        with open(catalog_file, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2, ensure_ascii=False)

        print(f"Saved {obj_key} to {catalog_name}.json")
        return True
    except Exception as e:
        print(f"Error saving to catalog: {e}")
        return False


# Catalog dictionaries - will be populated from JSON files on first use
MESSIER_DATA = {}
NGC_DATA = {}
IC_DATA = {}
CALDWELL_DATA = {}

# Catalog cache for lazy loading
_CATALOGS_LOADED = False


def _load_catalogs():
    """Lazy-load all astronomy catalogs to avoid startup CPU overhead."""
    global _CATALOGS_LOADED, NGC_DATA, IC_DATA, MESSIER_DATA, CALDWELL_DATA

    if _CATALOGS_LOADED:
        return

    print("Loading astronomy catalogs...")
    DATA_DIR = Path(__file__).parent / "data"

    # Load Messier catalog
    fp = DATA_DIR / "messier.json"
    if fp.exists():
        try:
            with open(fp, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    MESSIER_DATA.update(loaded)
                    print(f"  Loaded {len(MESSIER_DATA)} Messier objects")
        except Exception as e:
            print(f"Failed to load Messier catalog: {e}")

    # Load NGC catalog
    fp = DATA_DIR / "ngc.json"
    if fp.exists():
        try:
            with open(fp, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    NGC_DATA.update(loaded)
                    print(f"  Loaded {len(NGC_DATA)} NGC objects")
        except Exception as e:
            print(f"Failed to load NGC catalog: {e}")

    # Load IC catalog
    fp = DATA_DIR / "ic.json"
    if fp.exists():
        try:
            with open(fp, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    IC_DATA.update(loaded)
                    print(f"  Loaded {len(IC_DATA)} IC objects")
        except Exception as e:
            print(f"Failed to load IC catalog: {e}")

    # Load Caldwell catalog
    fp = DATA_DIR / "caldwell.json"
    if fp.exists():
        try:
            with open(fp, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    CALDWELL_DATA.update(loaded)
                    print(f"  Loaded {len(CALDWELL_DATA)} Caldwell objects")
        except Exception as e:
            print(f"Failed to load Caldwell catalog: {e}")

    _CATALOGS_LOADED = True


def normalize_object_name(name: str) -> str:
    """Normalize object name to standard format."""
    if not name:
        return name

    # Remove everything after parentheses or commas
    name = name.split("(")[0].split(",")[0].strip()

    # Normalize spacing
    name = " ".join(name.split())

    # Uppercase catalog prefixes
    for prefix in ["M", "NGC", "IC", "C"]:
        if name.upper().startswith(prefix):
            parts = name.split(None, 1)
            if len(parts) == 2:
                return prefix.upper() + parts[1]
            return name.upper()

    return name


def enrich_from_web(object_name: str) -> Optional[Dict[str, Any]]:
    """
    Enrich object information from web sources when local data is insufficient.
    Uses web search to find common names and basic information.
    """
    try:
        # Search for the object

        # Try to get basic info from a simple search
        # This is a placeholder - in production you'd use a proper API
        # For now, we'll return None and rely on manual catalog entries

        return None
    except Exception as e:
        print(f"Error enriching from web: {e}")
        return None


def get_object_info(object_name: str) -> Optional[Dict[str, Any]]:
    """
    Get astronomical object information.
    First checks cache, then tries local catalogs (Messier, IC), then PyONGC.
    """
    # Lazy-load catalogs on first object query
    _load_catalogs()

    normalized_name = normalize_object_name(object_name)

    # Check cache first
    cache_file = CACHE_DIR / f"{normalized_name}.json"
    cached_info = None
    if cache_file.exists():
        try:
            with open(cache_file, "r") as f:
                cached_info = json.load(f)
                # If cache is missing coordinates but object is in Messier/NGC/IC, refresh it
                if not cached_info.get("ra") or not cached_info.get("dec"):
                    print(f"[ASTRO INFO] Cache for {normalized_name} missing coordinates, refreshing...")
                    cached_info = None  # Force refresh
                else:
                    return cached_info
        except Exception:
            pass

    info = None

    # Try Messier catalog first (most common for amateur astrophotography)
    if normalized_name in MESSIER_DATA:
        info = MESSIER_DATA[normalized_name].copy()
        info["catalog"] = "Messier"
        info["designation"] = normalized_name
        print(f"[ASTRO INFO] Found {normalized_name} in Messier catalog: ra={info.get('ra')}, dec={info.get('dec')}")

    # Try NGC catalog for common NGC objects with popular names
    elif normalized_name in NGC_DATA:
        info = NGC_DATA[normalized_name].copy()
        info["catalog"] = "NGC"
        info["designation"] = normalized_name
        # If NGC catalog entry has no coordinates, try PyONGC
        if not info.get("ra") or not info.get("dec"):
            print(f"[ASTRO INFO] {normalized_name} in NGC catalog but missing coordinates, trying PyONGC...")
            info = None  # Will fall through to PyONGC

    # Try IC catalog for common IC objects with popular names
    elif normalized_name in IC_DATA:
        info = IC_DATA[normalized_name].copy()
        info["catalog"] = "IC"
        info["designation"] = normalized_name
        # If IC catalog entry has no coordinates, try PyONGC
        if not info.get("ra") or not info.get("dec"):
            print(f"[ASTRO INFO] {normalized_name} in IC catalog but missing coordinates, trying PyONGC...")
            info = None  # Will fall through to PyONGC

    # Try Caldwell catalog for Caldwell objects
    elif normalized_name in CALDWELL_DATA:
        info = CALDWELL_DATA[normalized_name].copy()
        info["catalog"] = "Caldwell"
        info["designation"] = normalized_name

    # Try PyONGC for NGC/IC objects (if not found in manual catalogs OR if they lack coordinates)
    if not info and (normalized_name.startswith("NGC") or normalized_name.startswith("IC")):
        ongc = _get_ongc()
        if ongc:
            try:
                # PyONGC might not handle leading zeros well, try both formats
                # First try with leading zeros (NGC0896)
                obj = ongc.get(normalized_name)

                # If not found, try without leading zeros (NGC896)
                if not obj:
                    # Remove leading zeros: NGC0896 -> NGC896
                    if normalized_name.startswith("NGC"):
                        no_zeros = "NGC" + normalized_name[3:].lstrip("0")
                    else:  # IC
                        no_zeros = "IC" + normalized_name[2:].lstrip("0")

                    print(f"[ASTRO INFO] PyONGC: {normalized_name} not found, trying {no_zeros}")
                    obj = ongc.get(no_zeros)

                if obj:
                    # Get common names from identifiers
                    common_names = []
                    if hasattr(obj, "identifiers") and obj.identifiers:
                        # identifiers returns: ('Messier', ['NGC'], ['IC'], ['common names'], ['other'])
                        if obj.identifiers[3]:  # Common names list
                            common_names = obj.identifiers[3]

                    info = {
                        "designation": normalized_name,
                        "name": common_names[0] if common_names else normalized_name,
                        "type": obj.type if hasattr(obj, "type") and obj.type else "Unknown",
                        "constellation": obj.constellation
                        if hasattr(obj, "constellation") and obj.constellation
                        else "Unknown",
                        "catalog": "NGC" if normalized_name.startswith("NGC") else "IC",
                    }

                    # Add coordinates if available
                    try:
                        if hasattr(obj, "rad_coords") and obj.rad_coords is not None:
                            # rad_coords returns numpy array([RA_radians, Dec_radians])
                            import numpy as np

                            ra_rad, dec_rad = obj.rad_coords
                            # Convert radians to degrees
                            info["ra"] = float(np.degrees(ra_rad))
                            info["dec"] = float(np.degrees(dec_rad))
                            print(
                                f"[ASTRO INFO] PyONGC coordinates for {normalized_name}: ra={info['ra']}, dec={info['dec']}"
                            )
                    except Exception as e:
                        print(f"[ASTRO INFO] Error extracting coordinates from PyONGC: {e}")

                    # Add magnitude if available
                    try:
                        if hasattr(obj, "magnitudes") and obj.magnitudes:
                            # magnitudes returns: (Bmag, Vmag, Jmag, Hmag, Kmag)
                            vmag = obj.magnitudes[1]  # V magnitude
                            if vmag is not None:
                                info["magnitude"] = f"{vmag}"
                    except:
                        pass

                    # Add size if available
                    try:
                        if hasattr(obj, "dimensions") and obj.dimensions:
                            # dimensions returns: (MajAx, MinAx, P.A.)
                            maj_ax, min_ax, pa = obj.dimensions
                            if maj_ax is not None and min_ax is not None:
                                info["size"] = f"{maj_ax}' x {min_ax}'"
                    except:
                        pass

                    # Add description based on type
                    obj_type = info["type"].lower()
                    if "galaxy" in obj_type:
                        info["description"] = f"A {info['type'].lower()} in the constellation {info['constellation']}."
                    elif "nebula" in obj_type:
                        info["description"] = f"A {info['type'].lower()} in the constellation {info['constellation']}."
                    elif "cluster" in obj_type:
                        info["description"] = f"A {info['type'].lower()} in the constellation {info['constellation']}."
                    else:
                        info["description"] = f"An astronomical object in the constellation {info['constellation']}."

                    # Save to local catalog for future queries
                    catalog_name = "ngc" if normalized_name.startswith("NGC") else "ic"
                    if _save_to_catalog(catalog_name, normalized_name, info):
                        # Update in-memory catalog
                        if catalog_name == "ngc":
                            NGC_DATA[normalized_name] = info
                        else:
                            IC_DATA[normalized_name] = info
            except Exception as e:
                print(f"Error fetching PyONGC data for {normalized_name}: {e}")
            finally:
                # Unload PyONGC to free memory
                _unload_ongc()

    # Cache the result if we found something
    if info:
        try:
            with open(cache_file, "w") as f:
                json.dump(info, f, indent=2)
        except Exception as e:
            print(f"Error caching object info: {e}")

    return info
