import os
import shutil
import zipfile
import tarfile
import importlib.util
from app.config_manager import ConfigManager
from app.file_dialog import FileDialog
from app.paths_module import get_plugins_dir


class PluginManager:
    def __init__(self, plugin_path="plugins", config: ConfigManager = None):
        self.plugin_path = str(get_plugins_dir("FreeM3UFileManager"))
        self.config = config or ConfigManager()
        # Dictionary: {plugin_name: {"instance": obj, "active": bool}}
        self.available_plugins = {}  # minimal info with scan_plugins
        self.plugins = {}  # loaded instances

    def load_plugins(self):
        """Load all .py plugins in plugin_path (recursive)"""
        self.plugins.clear()
        if not os.path.exists(self.plugin_path):
            return

        enabled_plugins = set(self.config.get_enabled_plugins())

        for root, _, files in os.walk(self.plugin_path):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    plugin_name = file[:-3]
                    file_path = os.path.join(root, file)

                    try:
                        spec = importlib.util.spec_from_file_location(plugin_name, file_path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)

                        plugin_class = getattr(module, "plugin_class", None)
                        if not plugin_class:
                            print(f"[PluginManager] {plugin_name} does not define plugin_class, ignored.")
                            continue

                        plugin = plugin_class(config_manager=self.config)

                        if not hasattr(plugin, "name") or not hasattr(plugin, "get_functions"):
                            print(f"[PluginManager] {plugin_name} invalid (missing name or get_functions), ignored.")
                            continue

                        is_active = plugin_name in enabled_plugins
                        self.plugins[plugin.name] = {
                            "instance": plugin,
                            "active": is_active
                        }

                        state = "ACTIVE" if is_active else "INACTIVE"
                        print(f"[PluginManager] Loaded plugin: {plugin.name} ({state})")

                    except Exception as e:
                        print(f"[PluginManager] Error loading {plugin_name}: {e}")


    def get_plugins(self):
        """Return all loaded plugins (active or inactive)"""
        return self.plugins

    def get_active_plugins(self):
        """Return only active plugin instances"""
        return [data["instance"] for data in self.plugins.values() if data["active"]]

    def toggle_plugin(self, plugin_name: str, state: bool):
        """Enable or disable a plugin by name and update config"""
        if plugin_name in self.plugins:
            self.plugins[plugin_name]["active"] = state
            self._save_enabled_plugins()

    def open_plugin_config(self, plugin_name, parent=None):
        """Open plugin-specific config if available"""
        if plugin_name in self.plugins:
            instance = self.plugins[plugin_name]["instance"]
            if hasattr(instance, "__open_plugin_config_menu"):
                instance.__open_plugin_config_menu(parent)
                return True
        return False

    def _save_enabled_plugins(self):
        """Save the list of active plugins in config"""
        enabled = [name for name, data in self.plugins.items() if data["active"]]
        self.config.set_enabled_plugins(enabled)

    def scan_plugins(self):
        """
        Scan plugin_path recursively and return minimal info:
        {plugin_name: {"class": plugin_class, "file": file_path}}
        """
        scanned = {}
        if not os.path.exists(self.plugin_path):
            return scanned

        for root, _, files in os.walk(self.plugin_path):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    plugin_name = file[:-3]
                    file_path = os.path.join(root, file)
                    try:
                        spec = importlib.util.spec_from_file_location(plugin_name, file_path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        plugin_class = getattr(module, "plugin_class", None)
                        if plugin_class:
                            scanned[plugin_name] = {
                                "class": plugin_class,
                                "file": file_path
                            }
                    except Exception as e:
                        print(f"[PluginManager] Error scanning {plugin_name}: {e}")
        return scanned


    def import_plugins(self, on_complete=None):
        """Open FileDialog to import plugins (.py or compressed)."""
        def callback(path):
            try:
                # Install the selected plugin
                installed_plugins = self._install_plugin_file(path)

                # Refresh the minimal list of plugins
                self.available_plugins = self.scan_plugins()
                print(f"[PluginManager] Plugins updated after import: {list(self.available_plugins.keys())}")

                # Add the newly installed plugins to config as enabled
                enabled = set(self.config.get_enabled_plugins())
                enabled.update(installed_plugins)
                self.config.set_enabled_plugins(list(enabled))

                # Call external callback (for example refresh_plugins) if provided
                if on_complete:
                    on_complete()

            except Exception as e:
                print(f"[PluginManager] Error importing {path}: {e}")

        # Open FileDialog **only once**
        FileDialog(
            mode="open",
            file_types=["*.py", "*.zip", "*.tar", "*.tar.gz", "*.tgz", "*.*"],
            title="Import Plugin",
            callback=callback
        ).open()


    def _install_plugin_file(self, filepath):
        """Install a plugin file (.py or compressed). Returns list of installed plugin names."""
        installed_plugins = []
        ext = os.path.splitext(filepath)[1].lower()
        os.makedirs(self.plugin_path, exist_ok=True)

        if ext == ".py":
            dest = os.path.join(self.plugin_path, os.path.basename(filepath))
            shutil.copy(filepath, dest)
            print(f"[PluginManager] Copied plugin: {dest}")
            installed_plugins.append(os.path.splitext(os.path.basename(dest))[0])

        elif ext == ".zip":
            with zipfile.ZipFile(filepath, "r") as zf:
                zf.extractall(self.plugin_path)
                for f in zf.namelist():
                    if f.endswith(".py") and not f.startswith("__"):
                        plugin_name = os.path.splitext(os.path.basename(f))[0]
                        installed_plugins.append(plugin_name)
            print(f"[PluginManager] Extracted ZIP: {filepath}")

        elif ext in [".tar", ".gz", ".tgz", ".tar.gz"]:
            with tarfile.open(filepath, "r:*") as tf:
                tf.extractall(self.plugin_path)
                for f in tf.getnames():
                    if f.endswith(".py") and not f.startswith("__"):
                        plugin_name = os.path.splitext(os.path.basename(f))[0]
                        installed_plugins.append(plugin_name)
            print(f"[PluginManager] Extracted TAR: {filepath}")

        else:
            raise ValueError(f"[PluginManager] Unsupported format: {filepath}")

        return installed_plugins
