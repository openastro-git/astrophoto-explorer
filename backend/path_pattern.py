"""Pattern-based path parser for flexible folder structure support.

Converts user-defined patterns like '$TARGETNAME$/$DATE$/masters' into
structured path parsers that extract metadata from file paths.

Supported variables:
    $TARGETNAME$ — astronomical object name
    $DATE$       — session date (YYYY-MM-DD)
    $FILTER$     — filter name (Ha, OIII, SII, L, R, G, B, etc.)
    $SESSION$    — session identifier (non-date)
    $ANY$        — wildcard, matches any folder (value is discarded)
"""
import os
import re
from pathlib import Path, PurePath
from typing import Optional


# All recognized variable tokens
VARIABLES = {
    '$TARGETNAME$': {
        'key': 'target_name',
        'description': 'Astronomical object / target name',
        # Match any folder name (will be normalized later)
        'regex': r'[^/\\]+',
    },
    '$DATE$': {
        'key': 'date',
        'description': 'Session date (YYYY-MM-DD)',
        'regex': r'\d{4}-\d{2}-\d{2}',
    },
    '$FILTER$': {
        'key': 'filter',
        'description': 'Filter name (e.g., Ha, OIII, L, R, G, B)',
        'regex': r'[^/\\]+',
    },
    '$SESSION$': {
        'key': 'session',
        'description': 'Session identifier',
        'regex': r'[^/\\]+',
    },
    '$ANY$': {
        'key': None,  # Value is discarded
        'description': 'Wildcard — matches any folder, value ignored',
        'regex': r'[^/\\]+',
    },
}

# Pattern to find $VARIABLE$ tokens in a pattern string
_TOKEN_RE = re.compile(r'\$[A-Z]+\$')


class PatternSegment:
    """A single segment in a parsed pattern (either a variable or a literal)."""

    __slots__ = ('is_variable', 'token', 'key', 'regex', 'literal')

    def __init__(self, *, is_variable: bool, token: str = '',
                 key: str = None, regex: str = None, literal: str = ''):
        self.is_variable = is_variable
        self.token = token          # e.g., '$TARGETNAME$'
        self.key = key              # e.g., 'target_name'
        self.regex = regex          # regex to match this segment
        self.literal = literal      # for literal segments

    def matches(self, part: str) -> bool:
        """Check if a path part matches this segment."""
        if self.is_variable:
            return bool(re.fullmatch(self.regex, part))
        else:
            return part.lower() == self.literal.lower()

    def __repr__(self):
        if self.is_variable:
            return f'Var({self.token})'
        return f'Lit({self.literal})'


class PathPattern:
    """Parses a user-defined folder pattern and extracts metadata from paths.

    Usage::

        pattern = PathPattern('$TARGETNAME$/$DATE$/masters')
        result = pattern.extract('M31/2025-06-15/masters/Ha_stack.fits',
                                 base_path='/data/astro')
        # result == {'target_name': 'M31', 'date': '2025-06-15'}
    """

    def __init__(self, pattern_str: str = ''):
        self.raw_pattern = pattern_str.strip()
        self.segments: list[PatternSegment] = []
        self._parse()

    def _parse(self):
        """Parse the raw pattern string into ordered segments."""
        if not self.raw_pattern:
            return

        # Normalize separators to forward slash
        normalized = self.raw_pattern.replace('\\', '/')

        # Split into parts
        parts = [p.strip() for p in normalized.split('/') if p.strip()]

        for part in parts:
            token_match = _TOKEN_RE.fullmatch(part)
            if token_match:
                token = part
                if token in VARIABLES:
                    var_info = VARIABLES[token]
                    self.segments.append(PatternSegment(
                        is_variable=True,
                        token=token,
                        key=var_info['key'],
                        regex=var_info['regex'],
                    ))
                else:
                    # Unknown variable — treat as literal
                    print(f"[PathPattern] Warning: unknown variable '{token}', treating as literal")
                    self.segments.append(PatternSegment(
                        is_variable=False,
                        literal=part,
                    ))
            else:
                # Literal path segment (e.g., 'masters', 'output')
                self.segments.append(PatternSegment(
                    is_variable=False,
                    literal=part,
                ))

    @property
    def is_empty(self) -> bool:
        """True if no pattern is configured (use fallback extraction)."""
        return len(self.segments) == 0

    @property
    def variable_keys(self) -> list[str]:
        """List of variable keys in this pattern (excluding $ANY$)."""
        return [s.key for s in self.segments if s.is_variable and s.key]

    def extract(self, file_path: str, base_path: str = None) -> Optional[dict]:
        """Extract metadata fields from a file path using this pattern.

        Args:
            file_path: Full or relative path to the file
            base_path: Base scan folder to strip before matching

        Returns:
            Dictionary with extracted fields, or None if the path
            doesn't match the pattern. Possible keys:
            'target_name', 'date', 'filter', 'session'
        """
        if self.is_empty:
            return None

        # Get relative path (normalized to forward slashes)
        rel_path = _get_relative_path(file_path, base_path)

        # Split on '/' to get parts, then drop the last part (filename)
        parts = [p for p in rel_path.split('/') if p]
        if len(parts) > 0:
            dir_parts = parts[:-1]  # Exclude filename
        else:
            dir_parts = []

        # Try to match segments against directory parts
        return self._match_segments(dir_parts)

    def _match_segments(self, dir_parts: list[str]) -> Optional[dict]:
        """Match pattern segments against directory parts.

        The pattern segments must match a contiguous prefix of the dir_parts.
        Any extra directories after the pattern are allowed (files can be
        nested deeper than the pattern specifies).
        """
        if len(dir_parts) < len(self.segments):
            return None

        result = {}
        for i, segment in enumerate(self.segments):
            part = dir_parts[i]

            if not segment.matches(part):
                return None

            if segment.is_variable and segment.key:
                result[segment.key] = part

        return result

    def describe(self) -> str:
        """Human-readable description of the pattern."""
        if self.is_empty:
            return "No pattern (auto-detect from path)"
        parts = []
        for seg in self.segments:
            if seg.is_variable:
                parts.append(seg.token)
            else:
                parts.append(seg.literal)
        return ' / '.join(parts)

    def __repr__(self):
        return f'PathPattern({self.raw_pattern!r})'

    def __str__(self):
        return self.raw_pattern or '(empty)'


def apply_ignore_filters(file_paths: list, ignore_filters: list[str]) -> list:
    """Filter out files whose relative path contains any of the ignore substrings.

    Args:
        file_paths: List of (file_path, file_type) tuples or plain path strings
        ignore_filters: List of substring filters (e.g., ['light/', 'dark/'])

    Returns:
        Filtered list with matching files removed
    """
    if not ignore_filters:
        return file_paths

    # Normalize filters: lowercase, ensure they use forward slashes
    normalized_filters = []
    for f in ignore_filters:
        f = f.strip()
        if f:
            normalized_filters.append(f.lower().replace('\\', '/'))

    if not normalized_filters:
        return file_paths

    filtered = []
    for item in file_paths:
        # Handle both tuple (file_path, file_type) and plain path
        if isinstance(item, tuple):
            path_str = str(item[0])
        else:
            path_str = str(item)

        # Normalize path for comparison
        normalized_path = path_str.lower().replace('\\', '/')

        # Check against each filter
        should_ignore = False
        for filt in normalized_filters:
            if filt in normalized_path:
                should_ignore = True
                break

        if not should_ignore:
            filtered.append(item)

    return filtered


def get_available_variables() -> list[dict]:
    """Return list of available pattern variables for UI display.

    Returns:
        List of dicts with 'token', 'key', 'description' for each variable
    """
    result = []
    for token, info in VARIABLES.items():
        result.append({
            'token': token,
            'key': info['key'] or 'any',
            'description': info['description'],
        })
    return result


def _get_relative_path(file_path: str, base_path: str = None) -> str:
    """Get the relative path, normalized to forward slashes.
    
    Uses pathlib.Path for OS-native path resolution, which correctly
    handles drive letters (Windows), case sensitivity (Linux/macOS),
    UNC paths, and mixed separator styles.
    """
    # Use pathlib for proper OS-aware path handling
    file_p = Path(str(file_path))
    
    if base_path:
        base_p = Path(str(base_path))
        try:
            # Try proper relative_to() first (handles drive letters, etc.)
            rel = file_p.relative_to(base_p)
            # Convert to forward-slash string
            return str(rel).replace(os.sep, '/')
        except ValueError:
            # relative_to() failed — paths may have different roots or
            # case mismatch on case-insensitive systems. Fall back to
            # string-based stripping with normalization.
            pass
        
        # Fallback: normalize both paths for string comparison
        # os.path.normcase handles case-folding on Windows, no-op on Unix
        file_norm = os.path.normcase(os.path.normpath(str(file_path)))
        base_norm = os.path.normcase(os.path.normpath(str(base_path)))
        
        # Ensure base ends with separator for clean stripping
        if not base_norm.endswith(os.sep):
            base_norm += os.sep
        
        if file_norm.startswith(base_norm):
            remainder = str(file_path)[len(str(base_path)):]
            # Strip any leading separators and normalize
            return remainder.lstrip('/\\').replace(os.sep, '/')
    
    # No base path — just normalize separators
    return str(file_path).replace(os.sep, '/').replace('\\', '/').lstrip('/')
