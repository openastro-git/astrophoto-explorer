import sys
import shutil
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent.parent
    build_dir = root / "build"
    ui_dir = build_dir / "ui"

    print(f"Root directory: {root}")
    print(f"Cleaning build directory: {build_dir}")

    # 1. Clean build folder
    if build_dir.exists():
        try:
            shutil.rmtree(build_dir)
        except Exception as e:
            print(f"Warning cleaning directory: {e}")
    build_dir.mkdir(parents=True, exist_ok=True)
    ui_dir.mkdir(parents=True, exist_ok=True)

    # 2. Copy backend
    print("Copying backend files...")
    shutil.copytree(root / "backend", build_dir / "backend")

    # 3. Copy frontend dist
    print("Copying frontend build files...")
    dist_dir = root / "dist"
    if not dist_dir.exists():
        print("Error: dist directory does not exist. Run 'npm run build' first.")
        sys.exit(1)
    shutil.copytree(dist_dir, ui_dir, dirs_exist_ok=True)

    # 4. Copy standalone_api.py and spec
    print("Copying standalone runner files...")
    shutil.copy(root / "standalone_api.py", build_dir / "standalone_api.py")
    shutil.copy(root / "standalone_api.spec", build_dir / "standalone_api.spec")

    # 5. Copy icon if exists
    icon_file = root / "icon.ico"
    if icon_file.exists():
        shutil.copy(icon_file, build_dir / "icon.ico")

    # Copy splash screen if exists
    splash_file = root / "splash_screen.png"
    if splash_file.exists():
        shutil.copy(splash_file, build_dir / "splash_screen.png")

    # 6. Copy pyongc database
    print("Locating pyongc database...")
    try:
        import pyongc

        pyongc_dir = Path(pyongc.__file__).parent
        db_file = pyongc_dir / "ongc.db"
        if db_file.exists():
            pyongc_data_dir = build_dir / "pyongc_data"
            pyongc_data_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(db_file, pyongc_data_dir / "ongc.db")
            print(f"[OK] Staged pyongc database from {db_file}")
        else:
            print(f"Error: ongc.db not found at {db_file}")
            sys.exit(1)
    except Exception as e:
        print(f"Error locating pyongc: {e}")
        sys.exit(1)

    print("Staging complete!")


if __name__ == "__main__":
    main()
