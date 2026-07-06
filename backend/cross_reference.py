"""Cross-reference utilities for catalog objects."""

import re
import json
import time
from pathlib import Path
from .object_naming import get_catalog_priority

# Cache for expensive cross-reference building
_JSON_CROSS_REFS_CACHE = None


def _load_json_catalog(catalog_name):
    """Load a JSON catalog file (messier, ngc, ic, caldwell)."""
    try:
        data_dir = Path(__file__).parent / "data"
        catalog_file = data_dir / f"{catalog_name}.json"
        if catalog_file.exists():
            with open(catalog_file, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading {catalog_name}.json: {e}")
    return {}


def _extract_catalog_designations_from_name(name_str):
    """
    Extract catalog designations from a name string.
    Examples: "NGC 6093" -> ["NGC6093"], "Messier 80" -> ["M80"]
    Returns a list of normalized designations (spaces removed, uppercase).
    """
    if not name_str:
        return []

    designations = []
    name_upper = name_str.strip().upper()

    # Pattern 1: NGC/IC with optional space (e.g., "NGC 6093", "IC 487")
    ngc_ic_matches = re.findall(r"(NGC|IC)\s*(\d+)", name_upper)
    for prefix, number in ngc_ic_matches:
        designations.append(f"{prefix}{number}")

    # Pattern 2: Messier with optional space (e.g., "Messier 80", "M 80", "M80")
    messier_matches = re.findall(r"(?:MESSIER|M)\s*(\d+)", name_upper)
    for number in messier_matches:
        designations.append(f"M{number}")

    # Pattern 3: Caldwell with optional space (e.g., "Caldwell 33", "C 33", "C33")
    # Use negative lookbehind and lookahead to avoid matching C inside NGC/IC
    caldwell_matches = re.findall(r"(?:CALDWELL|(?<!N)(?<!I)(?<!G)C)\s*(\d+)", name_upper)
    for number in caldwell_matches:
        # Double-check: don't include if it looks like it came from NGC or IC
        # (e.g., "NGC 6992" should not produce "C6992")
        if f"NG{number}" not in name_upper and f"I{number}" not in name_upper:
            designations.append(f"C{number}")

    return designations


def _build_json_cross_references():
    """
    Build cross-references from all catalog JSON files (cached at module level).
    Returns a dictionary mapping designations to their cross-references.
    """
    global _JSON_CROSS_REFS_CACHE

    # Return cached version if available
    if _JSON_CROSS_REFS_CACHE is not None:
        return _JSON_CROSS_REFS_CACHE

    start_time = time.time()
    json_refs = {}
    Path(__file__).parent / "data"

    # Load all catalog files
    catalogs = {
        "messier": _load_json_catalog("messier"),
        "ngc": _load_json_catalog("ngc"),
        "ic": _load_json_catalog("ic"),
        "caldwell": _load_json_catalog("caldwell"),
    }

    # Process each catalog and extract cross-references from the "name" field
    for catalog_name, catalog_data in catalogs.items():
        for obj_key, obj_data in catalog_data.items():
            if not isinstance(obj_data, dict):
                continue

            # Get the primary designation from the object
            primary_designation = None

            # Try to get designation from the object's designation field
            if "designation" in obj_data:
                primary_designation = obj_data["designation"].replace(" ", "").upper()
            elif "name" in obj_data and catalog_name == "messier":
                # For Messier, check if name is just "M1", "M2", etc.
                name_str = obj_data["name"].strip()
                if re.match(r"^M\s*\d+$", name_str, re.IGNORECASE):
                    primary_designation = name_str.replace(" ", "").upper()

            if not primary_designation:
                primary_designation = obj_key.replace(" ", "").upper()

            # Extract cross-references from the "name" and "other" fields
            extracted = []
            if "name" in obj_data:
                name_str = obj_data["name"]
                extracted.extend(_extract_catalog_designations_from_name(name_str))

            if "other" in obj_data:
                other_str = obj_data["other"]
                extracted.extend(_extract_catalog_designations_from_name(other_str))

            if extracted:
                # Store bidirectional references
                if primary_designation not in json_refs:
                    json_refs[primary_designation] = []
                for designation in extracted:
                    if designation != primary_designation and designation not in json_refs[primary_designation]:
                        json_refs[primary_designation].append(designation)

    elapsed = time.time() - start_time
    print(f"[PERF] Built JSON cross-references cache in {elapsed:.3f}s")

    # Cache the result
    _JSON_CROSS_REFS_CACHE = json_refs
    return json_refs


def get_cross_references(obj_name):
    """
    Get cross-references for an object (e.g., M31 = NGC224 = C23).
    Returns a list of equivalent designations.
    Uses JSON catalogs as the primary source of truth, with fallback to PyONGC library.

    For non-catalog descriptive names, returns them as-is without normalization.
    """
    # Check if this looks like a catalog object (contains catalog prefixes)
    catalog_pattern = re.compile(r"\b(M|NGC|IC|C|SH2-|LDN|ABELL)\s*\d+", re.IGNORECASE)
    is_catalog_object = catalog_pattern.search(obj_name) is not None

    # If it's not a catalog object, return as-is (preserve case and spacing)
    if not is_catalog_object:
        return [obj_name]

    # Load cross-references from JSON catalogs (primary source)
    json_cross_refs = _build_json_cross_references()

    # Minimal hardcoded mappings for special cases not in JSON
    hardcoded_special_cases = {
        "M40": ["WINNECKE4"],  # M40 is a special case - two stars
    }

    # Normalize input (only for catalog objects)
    obj_normalized = obj_name.replace(" ", "").upper()

    # Start with JSON cross-references as the source of truth
    cross_ref_map = json_cross_refs.copy()

    # Add special hardcoded cases
    for primary, alternates in hardcoded_special_cases.items():
        if primary not in cross_ref_map:
            cross_ref_map[primary] = []
        for alt in alternates:
            if alt not in cross_ref_map[primary]:
                cross_ref_map[primary].append(alt)

    # Build reverse mapping (bidirectional)
    reverse_map = {}
    for primary, alternates in cross_ref_map.items():
        # Add primary -> alternates
        if primary not in reverse_map:
            reverse_map[primary] = []
        reverse_map[primary].extend(alternates)

        # Add each alternate -> primary + other alternates
        for alt in alternates:
            if alt not in reverse_map:
                reverse_map[alt] = []
            if primary not in reverse_map[alt]:
                reverse_map[alt].append(primary)
            # Also add other alternates
            for other_alt in alternates:
                if other_alt != alt and other_alt not in reverse_map[alt]:
                    reverse_map[alt].append(other_alt)

    # Check reverse map (handles both directions)
    if obj_normalized in reverse_map:
        all_refs = [obj_normalized] + reverse_map[obj_normalized]
        # Remove duplicates while preserving order
        seen = set()
        unique_refs = []
        for ref in all_refs:
            if ref not in seen:
                seen.add(ref)
                unique_refs.append(ref)
        return unique_refs

    # Try PyONGC for NGC/IC objects if not in our map
    try:
        from pyongc import ongc

        if ongc and (obj_normalized.startswith("NGC") or obj_normalized.startswith("IC")):
            obj = ongc.get(obj_normalized)
            if obj:
                # Get identifiers from PyONGC
                identifiers = [obj_normalized]

                # Check if it has a Messier designation
                if hasattr(obj, "getIdentifiers"):
                    ids = obj.getIdentifiers()
                    if ids:
                        for id_str in ids:
                            id_normalized = id_str.replace(" ", "").upper()
                            if id_normalized not in identifiers:
                                identifiers.append(id_normalized)

                if len(identifiers) > 1:
                    return identifiers
    except Exception as e:
        print(f"PyONGC lookup failed for {obj_normalized}: {e}")

    # No cross-references found
    return [obj_normalized]


def get_canonical_name(obj_name):
    """
    Get the canonical (preferred) name for an object.
    Prefers M > NGC > C > IC > Others
    """
    cross_refs = get_cross_references(obj_name)

    # Sort by priority and return the highest priority name
    sorted_refs = sorted(cross_refs, key=get_catalog_priority)
    return sorted_refs[0] if sorted_refs else obj_name
