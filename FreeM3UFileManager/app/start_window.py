# app/start_window.py
# -*- coding: utf-8 -*-
import os
import time
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.clock import Clock
from kivy.properties import ObjectProperty
from kivy.graphics import Rectangle, Color

from app.themed_screen import ThemedScreen
from app.config_manager import ConfigManager
from app.plugin_manager import PluginManager
from app.editor_main_window import EditorMainWindow
from app.file_dialog import FileDialog
from app.style_manager import style_manager  # Puedes adaptar para Kivy si quieres tema oscuro
from app.paths_module import *

class StartWindow(ThemedScreen):
    editor = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        path = get_user_data_dir()
        plugins_path = get_plugins_dir()
        ensure_dir(path)
        ensure_dir(plugins_path)

        # --- Config & Plugin Manager ---
        self.config = ConfigManager()
        self.plugin_manager = PluginManager(config=self.config)
        self.plugin_manager.available_plugins = self.plugin_manager.scan_plugins()

        # Activar/desactivar plugins según config
        enabled_plugins = set(self.config.get_enabled_plugins())
        for plugin_name in self.plugin_manager.get_plugins():
            self.plugin_manager.toggle_plugin(plugin_name, plugin_name in enabled_plugins)

        self.last_file = self.config.get("last_file", "")
        self.dark_mode = self.config.get_bool("dark_mode", True)
        # Aquí podrías aplicar un estilo Kivy si quieres:
        self.style_manager = style_manager
        self.style = []
        self.apply_style()
        # self.apply_style(get_stylesheet(self.dark_mode))

        # --- Layout ---
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        self.add_widget(layout)

        self.top_layout = BoxLayout(orientation='horizontal', spacing=10, padding=10, size_hint=(1,.2))
        self.top_layout.add_widget(Label(text="FREE M3U FILE MANAGER", font_size=56))
        layout.add_widget(self.top_layout)

        self.new_button = Button(text="New M3U File", size_hint=(1,.2), font_size=28)
        self.load_button = Button(text="Load M3U File", size_hint=(1,.2), font_size=28)
        layout.add_widget(self.new_button)
        layout.add_widget(self.load_button)

        if self.last_file and os.path.exists(self.last_file):
            file_name = os.path.basename(self.last_file)
            self.last_button = Button(text=f"Load last file:\n{file_name}", size_hint=(1,.2), font_size=28)
            layout.add_widget(self.last_button)
            self.last_button.bind(on_release=lambda btn: self.load_last_file())

        self.config_button = Button(text="Settings", size_hint=(1,.2), font_size=28)
        layout.add_widget(self.config_button)
        self.config_button.bind(on_release=lambda btn: self.open_config_window())

        self.new_button.bind(on_release=lambda btn: self.create_new_file())
        self.load_button.bind(on_release=lambda btn: self.load_file())

        # Popup y worker
        self.loading_popup = None
        self.loader_worker = None


    def apply_style(self):
        self.style_manager.set_style(self.config.get_bool("dark_mode", True) if self.config else True)
        self.style = style_manager.get_style()
            
        bg_color = self.style.get("window_background_color", (0.1, 0.1, 0.1, 1))
        self.set_background_color(bg_color)

    # ------------------- Worker y Loading Popup internos -------------------
    class PluginLoaderWorker:
        def __init__(self, plugin_manager, progress_callback, finished_callback):
            self.plugin_manager = plugin_manager
            self.progress_callback = progress_callback
            self.finished_callback = finished_callback

        def run(self):
            self.progress_callback("Scanning plugins...")
            self.plugin_manager.available_plugins = self.plugin_manager.scan_plugins()

            total = len(self.plugin_manager.available_plugins)
            count = 0
            for name, info in self.plugin_manager.available_plugins.items():
                self.progress_callback(f"Loading plugin: {name} ({count+1}/{total})")
                plugin_class = info["class"]
                plugin_instance = plugin_class(config_manager=self.plugin_manager.config)
                if hasattr(plugin_instance, "name") and hasattr(plugin_instance, "get_functions"):
                    is_active = name in self.plugin_manager.config.get_enabled_plugins()
                    self.plugin_manager.plugins[plugin_instance.name] = {
                        "instance": plugin_instance,
                        "active": is_active
                    }
                count += 1

            self.progress_callback("Plugins loaded successfully!")
            Clock.schedule_once(lambda dt: self.finished_callback())

    class LoadingPopup(Popup):
        def __init__(self, **kwargs):
            super().__init__(title="Loading...", size_hint=(1,1), auto_dismiss=False, **kwargs)
            layout = BoxLayout(orientation='vertical', spacing=10, padding=20)
            self.label = Label(text="Loaging plugins...", size_hint_y=None, height=40, font_size=24)
            self.progress = ProgressBar(max=1, value=0, height=20)
            layout.add_widget(self.label)
            layout.add_widget(self.progress)
            self.content = layout

        def set_message(self, msg):
            self.label.text = msg

    # ------------------- Abrir editor con carga asíncrona -------------------
    def open_editor(self, file_path, is_new):
        self.loading_popup = self.LoadingPopup()
        self.loading_popup.open()

        self.loader_worker = self.PluginLoaderWorker(
            self.plugin_manager,
            progress_callback=lambda msg: Clock.schedule_once(lambda dt: self.loading_popup.set_message(msg)),
            finished_callback=lambda: self._on_plugins_loaded(file_path, is_new)
        )
        Clock.schedule_once(lambda dt: self.loader_worker.run())

    def _on_plugins_loaded(self, file_path, is_new):
        if self.loading_popup:
            self.loading_popup.dismiss()
            self.loading_popup = None

        # Crear y cambiar de Screen
        editor_main_window_screen = EditorMainWindow(file_path, is_new, config=self.config, plugin_manager=self.plugin_manager)
        self.parent.add_widget(editor_main_window_screen)
        self.parent.current = "editor"  # Transiciona al editor

    # ------------------- Operaciones normales -------------------

    def create_new_file(self):
        def on_file_selected(path):
            # Aquí podrías inicializar el archivo vacío
            with open(path, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
            self.config.set("last_file", path)
            self.open_editor(path, True)

        dialog = FileDialog(
            mode="new",
            title="Create New M3U File",
            default_path=os.getcwd(),
            callback=on_file_selected
        )
        dialog.open()

    def load_file(self):
        def on_file_selected(path):
            self.config.set("last_file", path)
            self.open_editor(path, False)

        dialog = FileDialog(
            mode="open",
            title="Select M3U File",
            default_path=os.getcwd(),
            callback=on_file_selected
        )

        dialog.open()

    def load_last_file(self):
        if self.last_file and os.path.exists(self.last_file):
            self.open_editor(self.last_file, False)
        else:
            from kivy.uix.popup import Popup
            from kivy.uix.label import Label
            popup = Popup(title="Error", content=Label(text="Last file not found."), size_hint=(0.5, 0.3))
            popup.open()

    def open_config_window(self):
        from app.config_manager import ConfigWindow
        # En Kivy podrías usar una pantalla o popup en lugar de exec_()
        cfg_screen = ConfigWindow(self.config, self.plugin_manager)
        self.parent.add_widget(cfg_screen)
        self.parent.current = cfg_screen.name
