#!/usr/bin/env python3
"""
Clean catalog JSON files:
- Normalize UTF-8 and remove non-visible characters
- Fix spacing around punctuation marks
"""

import json
import re
import unicodedata
from pathlib import Path


def clean_text(text):
    """Clean text by normalizing UTF-8, removing non-visible characters, and fixing punctuation/parentheses spacing."""
    if not isinstance(text, str):
        return text

    # Step 1: Normalize Unicode to NFD (decomposed form) then back to NFC (composed form)
    # This helps with combining diacritics and non-visible characters
    text = unicodedata.normalize("NFD", text)
    text = unicodedata.normalize("NFC", text)

    # Step 2: Remove non-visible and zero-width characters
    non_visible_chars = {
        "\u00ad": "",  # soft hyphen
        "\u200b": "",  # zero-width space
        "\u200c": "",  # zero-width non-joiner
        "\u200d": "",  # zero-width joiner
        "\u2060": "",  # word joiner
        "\ufeff": "",  # zero-width no-break space (BOM)
        "\u202f": " ",  # narrow no-break space -> regular space
        "\u00a0": " ",  # non-breaking space -> regular space
        "\u3000": " ",  # ideographic space -> regular space
    }

    for char, replacement in non_visible_chars.items():
        text = text.replace(char, replacement)

    # Step 3: Remove other control characters (except newline, tab, carriage return)
    text = "".join(ch if unicodedata.category(ch)[0] != "C" or ch in "\n\t\r" else "" for ch in text)

    # Step 4: Fix spacing around punctuation
    # Remove space before punctuation marks: . , ; : ! ?
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)

    # Step 5: Ensure space after punctuation (except at end of string)
    # Add space after . , ; : ! ? if followed by a letter or digit (and not already a space)
    text = re.sub(r"([.,;:!?])([A-Za-z0-9])", r"\1 \2", text)

    # Step 6: Fix spacing around parentheses
    # Normalize multiple spaces before opening parenthesis to single space: "word  (" -> "word ("
    text = re.sub(r"\s+\(", " (", text)
    # Remove space after opening parenthesis: "( word" -> "(word"
    text = re.sub(r"\(\s+", "(", text)
    # Remove space before closing parenthesis: "word )" -> "word)"
    text = re.sub(r"\s+\)", ")", text)
    # Ensure space after closing parenthesis if followed by letter/digit: ")word" -> ") word"
    text = re.sub(r"\)([A-Za-z0-9])", r") \1", text)

    # Step 7: Normalize multiple spaces to single space
    text = re.sub(r" +", " ", text)

    # Step 8: Strip leading/trailing whitespace
    text = text.strip()

    return text


def clean_catalog_file(filepath):
    """Clean a catalog JSON file."""
    print(f"Cleaning {filepath}...")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  Error loading {filepath}: {e}")
        return

    cleaned_count = 0

    # Clean all text fields in the catalog
    for key, obj in data.items():
        if isinstance(obj, dict):
            for field_name, field_value in obj.items():
                if isinstance(field_value, str):
                    cleaned_value = clean_text(field_value)
                    if cleaned_value != field_value:
                        obj[field_name] = cleaned_value
                        cleaned_count += 1

    # Write back
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  [OK] Cleaned {cleaned_count} fields")
    except Exception as e:
        print(f"  Error writing {filepath}: {e}")


def main():
    """Clean all catalog files."""
    data_dir = Path(__file__).parent.parent / "data"

    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}")
        return

    catalog_files = [
        data_dir / "messier.json",
        data_dir / "ngc.json",
        data_dir / "ic.json",
        data_dir / "caldwell.json",
    ]

    for filepath in catalog_files:
        if filepath.exists():
            clean_catalog_file(filepath)
        else:
            print(f"Skipping {filepath} (not found)")

    print("\n[OK] Catalog cleanup complete!")


if __name__ == "__main__":
    main()
