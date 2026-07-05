import sys
import os
import threading
import time
import json
from pathlib import Path

# Setup base directory and working directory depending on whether running frozen or as a script
if getattr(sys, 'frozen', False):
    # Running as bundled executable (PyInstaller)
    base_dir = Path(sys.executable).parent
else:
    # Running as development script
    base_dir = Path(__file__).resolve().parent

os.chdir(base_dir)
sys.path.insert(0, str(base_dir))

# Enable WebGL hardware acceleration on Linux (WebKitGTK)
if sys.platform.startswith("linux"):
    print("[INIT] Linux detected. Configuring WebKitGTK hardware acceleration environment variables...")
    os.environ["WEBKIT_DISABLE_COMPOSITING_MODE"] = "0"
    os.environ["WEBKIT_FORCE_SANDBOX"] = "0"
    # Ensure hardware acceleration isn't bypassed
    if "LIBGL_ALWAYS_SOFTWARE" in os.environ:
        del os.environ["LIBGL_ALWAYS_SOFTWARE"]

# Import backend modules after setting up paths
from backend.main import app
import uvicorn

def read_server_config():
    """Read host and port settings from config.json, with fallbacks."""
    host = "127.0.0.1"
    port = 8000
    config_path = base_dir / "config.json"
    
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
                host = config.get("api", {}).get("host", "127.0.0.1")
                port = config.get("api", {}).get("port", 8000)
        except Exception as e:
            print(f"[WARN] Error reading config.json: {e}. Using defaults.")
    return host, port

def start_api_server(host, port):
    """Run the FastAPI/Uvicorn server."""
    try:
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=True,
            use_colors=True
        )
    except Exception as e:
        print(f"[ERROR] FastAPI server failed: {e}")

def main():
    host, port = read_server_config()
    
    print("\n" + "="*50)
    print("Astrophoto Explorer stand-alone GUI")
    print("="*50)
    print(f"[START] Starting background API server at http://{host}:{port}...")
    
    # 1. Start FastAPI server in a background daemon thread
    server_thread = threading.Thread(target=start_api_server, args=(host, port), daemon=True)
    server_thread.start()
    
    # 2. Wait for the API server to become ready by checking the socket port
    import socket
    start_time = time.time()
    server_ready = False
    print(f"[INIT] Waiting for background API server to bind to {host}:{port}...")
    while time.time() - start_time < 3.0:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.1)
                s.connect((host, port))
                server_ready = True
                break
        except (socket.error, ConnectionRefusedError):
            time.sleep(0.05)
            
    if not server_ready:
        print(f"[WARN] API server at http://{host}:{port} did not start within timeout. Attempting to launch GUI anyway.")
    else:
        print(f"[INIT] API server is ready after {time.time() - start_time:.3f} seconds.")
    
    # Close PyInstaller splash screen before showing GUI window
    try:
        import pyi_splash
        pyi_splash.close()
        print("[INIT] Splash screen closed.")
    except ImportError:
        pass
        
    # 3. Import and launch PyWebView native window
    # Importing webview inside main avoids initializing GUI loops during CLI-only workflows
    import webview
    
    window_url = f"http://{host}:{port}"
    print(f"[GUI] Opening native window loading {window_url}")
    
    webview.create_window(
        title="Astrophoto Explorer",
        url=window_url,
        width=1280,
        height=800,
        resizable=True,
        min_size=(800, 600)
    )
    
    # Start the PyWebView event loop. This blocks until the window is closed.
    webview.start()
    
    # 4. Cleanup when the GUI window is closed
    print("[EXIT] Window closed. Shutting down application gracefully...")
    # Forceful exit to cleanly close all daemon sockets and background processing threads
    os._exit(0)

if __name__ == "__main__":
    if sys.platform == "win32":
        import multiprocessing
        multiprocessing.freeze_support()
    try:
        main()
    except Exception as e:
        import traceback
        with open("crash_log.txt", "w", encoding="utf-8") as f:
            f.write(f"Crash detected on startup:\n")
            traceback.print_exc(file=f)
        os._exit(1)
