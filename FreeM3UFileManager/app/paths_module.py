# paths_module.py
import os
import platform
from pathlib import Path

def get_user_data_dir(app_name="FreeM3UFileManager"):
    system = platform.system()

    if system == "Windows":
        base = Path(os.getenv("APPDATA", Path.home()))
        return base / app_name

    elif system == "Darwin":  # macOS
        base = Path.home() / "Library" / "Application Support"
        return base / app_name

    elif system == "Linux":
        base = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
        return base / app_name

    elif system == "Java":  # Android with Kivy/Buildozer reports "Java"
        try:
            from android.storage import app_storage_path
            return Path(app_storage_path()) / app_name
        except ImportError:
            return Path.home() / f".{app_name}"

    else:
        return Path.home() / f".{app_name}"


def get_config_file(app_name="FreeM3UFileManager"):
    system = platform.system()

    base_path = get_user_data_dir()
    config_file_name = "config.cfg"
    return base_path / config_file_name


def get_plugins_dir(app_name="FreeM3UFileManager"):
    system = platform.system()

    if system == "Windows":
        base = Path(os.getenv("APPDATA", Path.home()))
        path = base / app_name / "plugins"

    elif system == "Darwin":  # macOS
        path = Path.home() / "Library" / "Application Support" / app_name / "plugins"

    elif system == "Linux":
        path = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local/share")) / app_name / "plugins"

    elif system == "Java":  # Android (when using Kivy/Buildozer)
        try:
            from android.storage import app_storage_path
            path = Path(app_storage_path()) / app_name / "plugins"
        except ImportError:
            path = Path.home() / f".{app_name}" / "plugins"

    else:
        path = Path.home() / f".{app_name}" / "plugins"

    path.mkdir(parents=True, exist_ok=True)
    return path


def get_cache_dir(app_name="FreeM3UFileManager"):
    system = platform.system()

    if system == "Windows":
        base = Path(os.getenv("LOCALAPPDATA", Path.home()))
        return base / app_name / "Cache"

    elif system == "Darwin":
        return Path.home() / "Library" / "Caches" / app_name

    elif system == "Linux":
        base = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))
        return base / app_name

    elif system == "Java":  # Android
        try:
            from android.storage import app_storage_path
            return Path(app_storage_path()) / app_name / "cache"
        except ImportError:
            return Path.home() / f".{app_name}" / "cache"

    else:
        return Path.home() / f".{app_name}" / "cache"


def ensure_dir(path: Path):
    """Create the folder if it does not exist."""
    path.mkdir(parents=True, exist_ok=True)
    return path
