#!/usr/bin/env python3
"""
Icon Generator for Astrophoto Explorer
Converts a PNG image to ICO format for Windows executable
"""

from PIL import Image
import sys


def create_icon(input_path, output_path="icon.ico"):
    """
    Convert an image to Windows ICO format with multiple sizes

    Args:
        input_path: Path to input image (PNG, JPG, etc.)
        output_path: Path to output ICO file (default: icon.ico)
    """
    try:
        # Open the image
        img = Image.open(input_path)

        # Convert to RGBA if needed
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        # Create icon with multiple sizes (Windows standard)
        icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

        # Save as ICO with multiple sizes
        img.save(output_path, format="ICO", sizes=icon_sizes)

        print(f"[OK] Icon created successfully: {output_path}")
        print(f"  Sizes included: {', '.join([f'{w}x{h}' for w, h in icon_sizes])}")

    except FileNotFoundError:
        print(f"[FAIL] Error: Input file not found: {input_path}")
        sys.exit(1)
    except Exception as e:
        print(f"[FAIL] Error creating icon: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python create_icon.py <input_image> [output.ico]")
        print("\nExample:")
        print("  python create_icon.py logo.png")
        print("  python create_icon.py logo.png custom_icon.ico")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "icon.ico"

    create_icon(input_file, output_file)
