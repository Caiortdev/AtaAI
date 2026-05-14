"""Entry point for PyInstaller-bundled backend server."""
import multiprocessing
import sys
import os

# Ensure the app module is importable when running as frozen exe
if getattr(sys, 'frozen', False):
    # PyInstaller extracts to a temp dir accessible via sys._MEIPASS
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    if base_path not in sys.path:
        sys.path.insert(0, base_path)
    # Set working directory to exe location for storage/database paths
    os.chdir(os.path.dirname(sys.executable))

if __name__ == "__main__":
    multiprocessing.freeze_support()
    import uvicorn
    from app.main import app, initialize_database

    initialize_database()
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
