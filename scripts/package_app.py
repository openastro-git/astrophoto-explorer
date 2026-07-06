import sys
import shutil
import json
from datetime import date
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent.parent
    build_dir = root / "build"
    final_dir = build_dir / "AstrophotoExplorer"

    print(f"[PACK] Packaging app inside: {final_dir}")

    # 1. Clean and create final directory
    if final_dir.exists():
        try:
            shutil.rmtree(final_dir)
        except Exception as e:
            print(f"[WARN] Error cleaning final package directory: {e}")
    final_dir.mkdir(parents=True, exist_ok=True)

    # 2. Copy the compiled application and all its dependencies (onedir mode support)
    ext = ".exe" if sys.platform == "win32" else ""
    executable_name = f"astrophoto-explorer{ext}"
    src_dir = build_dir / "dist" / "astrophoto-explorer"

    if src_dir.exists() and src_dir.is_dir():
        print(f"[PACK] Staging compiled application and dependencies from directory: {src_dir}")
        shutil.copytree(src_dir, final_dir, dirs_exist_ok=True)
    else:
        # Fallback to copy single file if built with onefile
        src_exe = build_dir / "dist" / executable_name
        if not src_exe.exists():
            found_exes = list(build_dir.glob(f"**/astrophoto-explorer{ext}"))
            if found_exes:
                src_exe = found_exes[0]

        if not src_exe.exists():
            print(f"[ERROR] Compiled application '{executable_name}' not found in {build_dir}/dist!")
            sys.exit(1)

        print(f"[PACK] Staging compiled executable from: {src_exe}")
        shutil.copy(src_exe, final_dir / executable_name)

    # 3. Copy UI directory
    print("[PACK] Staging UI assets...")
    shutil.copytree(build_dir / "ui", final_dir / "ui", dirs_exist_ok=True)

    # 4. Generate default config.json
    print("[PACK] Creating default config.json...")
    config = {
        "version": "1.0.0",
        "build_date": str(date.today()),
        "default_folder": ".",
        "api": {"host": "127.0.0.1", "port": 8000},
        "ui": {"title": "Astrophoto Explorer", "auto_open_browser": True},
        "stretch": {
            "target_background": 0.25,
            "shadows_clipping": -2.8,
            "contrast_boost": 1.1,
            "linked_channels": False,
        },
        "cache": {"enabled": True, "directory": "./cache", "max_size_mb": 1024},
    }

    with open(final_dir / "config.json", "w") as f:
        json.dump(config, f, indent=2)

    # 5. Create final cache directory
    (final_dir / ".cache").mkdir(exist_ok=True)

    # 6. Copy favorites.json if it exists in dev
    favs_dev = root / ".cache" / "favorites.json"
    if favs_dev.exists():
        shutil.copy(favs_dev, final_dir / ".cache" / "favorites.json")
        print("[PACK] Copied favorites.json from development environment.")

    # 7. Create README.txt
    print("[PACK] Writing README.txt...")
    readme_content = f"""Astrophoto Explorer - Standalone Version 1.0.0
==========================================================

Welcome to Astrophoto Explorer! This is a self-contained desktop version.

Quick Start:
---------------
1. Double-click the astrophoto-explorer executable to launch the app.
2. The native desktop application window will open automatically.

Package Contents:
-------------------
- astrophoto-explorer{ext}: The desktop application and backend API server.
- ui/: The web interface files.
- config.json: Configuration settings (customizable).

Configuration:
----------------
Edit config.json to customize:
- Default folder for FITS files
- API host and port
- Image stretching parameters
- Cache settings

Troubleshooting:
------------------
If the application doesn't start:
1. Ensure your antivirus or firewall isn't blocking local loopback ports (default: 8000).
2. Check that port 8000 is not in use by another application.
3. On Linux: Make sure you have libwebkit2gtk-4.0 or libwebkit2gtk-4.1 installed.

(c) Astrophoto Explorer. Built with FastAPI, React, and Astropy.
"""
    with open(final_dir / "README.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)

    # 8. Create version.txt
    print("[PACK] Stamping version.txt...")
    with open(final_dir / "version.txt", "w") as f:
        f.write("1.0.0\n")
        f.write(f"Built on: {date.today()}\n")

    # 9. Clean up staging folders inside build/
    print("[PACK] Cleaning up temporary build staging files...")
    staging_dirs = ["venv", "backend", "ui", "pyongc_data", "dist", "build"]
    for s_dir in staging_dirs:
        p = build_dir / s_dir
        if p.exists() and p.is_dir():
            shutil.rmtree(p, ignore_errors=True)

    for f in build_dir.glob("standalone_api.*"):
        if f.is_file():
            try:
                f.unlink()
            except Exception as e:
                print(f"[WARN] Error removing temp file {f}: {e}")

    print("[PACK] Staging packaging completed successfully!")


if __name__ == "__main__":
    main()
