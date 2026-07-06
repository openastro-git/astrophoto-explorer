#!/usr/bin/env python3
"""
Generate Astrophoto Explorer Icon
Creates a sparkles icon matching the web interface design
"""

from PIL import Image, ImageDraw
import math


def draw_sparkle(draw, cx, cy, size, color, rotation=0):
    """Draw a single sparkle (4-pointed star)"""
    # Calculate points for a 4-pointed star
    points = []

    # Outer points (4 main points)
    for i in range(4):
        angle = math.radians(i * 90 + rotation)
        x = cx + size * math.cos(angle)
        y = cy + size * math.sin(angle)
        points.append((x, y))

        # Inner points (between main points)
        angle_inner = math.radians(i * 90 + 45 + rotation)
        inner_size = size * 0.3
        x_inner = cx + inner_size * math.cos(angle_inner)
        y_inner = cy + inner_size * math.sin(angle_inner)
        points.append((x_inner, y_inner))

    # Draw the sparkle
    draw.polygon(points, fill=color)


def create_sparkles_icon(size=256):
    """Create a sparkles icon matching the lucide design"""
    # Create image with transparency
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Cyan-400 color from Tailwind (#22d3ee)
    cyan = (34, 211, 238, 255)

    # Add a subtle dark background circle for better visibility
    bg_color = (15, 23, 42, 255)  # slate-900
    margin = size * 0.05
    draw.ellipse([margin, margin, size - margin, size - margin], fill=bg_color)

    # Draw three sparkles at different positions and sizes
    # Main sparkle (center-right, larger)
    main_x = size * 0.58
    main_y = size * 0.5
    main_size = size * 0.22
    draw_sparkle(draw, main_x, main_y, main_size, cyan, rotation=0)

    # Top-left sparkle (smaller)
    small_x = size * 0.32
    small_y = size * 0.28
    small_size = size * 0.12
    draw_sparkle(draw, small_x, small_y, small_size, cyan, rotation=15)

    # Bottom-left sparkle (medium)
    medium_x = size * 0.35
    medium_y = size * 0.68
    medium_size = size * 0.16
    draw_sparkle(draw, medium_x, medium_y, medium_size, cyan, rotation=-10)

    return img


def main():
    """Generate icon in multiple sizes and save as ICO"""
    print("Generating Astrophoto Explorer icon...")

    # Generate base image at high resolution
    base_img = create_sparkles_icon(256)

    # Create icon with multiple sizes for Windows
    icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

    # Save as ICO
    base_img.save("icon.ico", format="ICO", sizes=icon_sizes)
    print("[OK] Icon created: icon.ico")
    print(f"  Sizes: {', '.join([f'{w}x{h}' for w, h in icon_sizes])}")

    # Also save as PNG for preview
    base_img.save("icon_preview.png", format="PNG")
    print("[OK] Preview created: icon_preview.png")

    print("\nIcon matches the sparkles design from your web interface!")
    print("Color: Cyan-400 (#22d3ee)")
    print("\nRun build.bat to create the executable with this icon.")


if __name__ == "__main__":
    main()
