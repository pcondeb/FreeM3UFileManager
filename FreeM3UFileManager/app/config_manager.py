# app/config_manager.py
# -*- coding: utf-8 -*-
import configparser
import os
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.checkbox import CheckBox
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.core.window import Window
from app.paths_module import get_config_file


class ConfigManager:
    def __init__(self, config_file=str(get_config_file())):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self._load()

    def _load(self):
        """Load config from disk or create defaults"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file, encoding="utf-8")
        else:
            self.config["GENERAL"] = {
                "last_file": "",
                "dark_mode": "true"
            }
            self.config["PLUGINS"] = {
                "enabled": ""  # list of plugin names separated by commas
            }
            self.save()

    # --- General getters/setters ---
    def get(self, key, default="", section="GENERAL"):
        return self.config.get(section, key, fallback=default)

    def get_bool(self, key, default=True, section="GENERAL"):
        val = self.get(key, str(default), section).lower()
        return val in ["1", "true", "yes"]

    def set(self, key, value, section="GENERAL"):
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = str(value)
        self.save()

    # --- Plugin management ---
    def get_enabled_plugins(self):
        """Return list of enabled plugin names"""
        raw = self.get("enabled", "", section="PLUGINS")
        return [p.strip() for p in raw.split(",") if p.strip()]

    def set_enabled_plugins(self, plugin_list):
        """Save enabled plugin names as comma-separated string"""
        value = ",".join(plugin_list)
        self.set("enabled", value, section="PLUGINS")

    # --- Save to disk ---
    def save(self):
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)


# --- ConfigWindow (Kivy version) ---
class ConfigWindow(Screen):
    """
    Main settings: general + plugins
    Rows horizontally centered, center column fixed at 50% of screen width.
    """

    LEFT_WIDTH = 40  
    RIGHT_WIDTH = 100  
    ROW_HEIGHT = 40

    def __init__(self, config_manager, plugin_manager, **kwargs):
        super().__init__(**kwargs)
        self.name = "config"
        self.config_manager = config_manager
        self.plugin_manager = plugin_manager
        self.plugin_widgets = {}

        self.CENTER_WIDTH = Window.width * 0.5  # Fixed width label, centered: 50% of screen width

        root_layout = BoxLayout(orientation="vertical", padding=10, spacing=10)

        # --- General Settings ---
        root_layout.add_widget(Label(text="General settings:", size_hint_y=None, height=30))

        # Fila: Dark mode
        row = self._make_row(
            left_widget=CheckBox(active=self.config_manager.get_bool("dark_mode", True)),
            center_text="Enable dark mode",
            right_widget=None
        )
        self.dark_mode_cb = row["left"]  # We store a reference to the checkbox.
        root_layout.add_widget(row["layout"])

        # --- Plugin Settings ---
        root_layout.add_widget(Label(text="Plugins:", size_hint_y=None, height=30))

        scroll = ScrollView(size_hint=(1, 1))
        self.plugin_container = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
        self.plugin_container.bind(minimum_height=self.plugin_container.setter('height'))
        scroll.add_widget(self.plugin_container)
        root_layout.add_widget(scroll)

        # --- Botones Save / Cancel ---
        btn_layout = BoxLayout(orientation="horizontal", size_hint_y=None, height=50, spacing=10)
        save_btn = Button(text="Save")
        cancel_btn = Button(text="Cancel")
        save_btn.bind(on_release=self.save_config)
        cancel_btn.bind(on_release=lambda *_: setattr(self.manager, 'current', 'start_window') if self.manager else None)
        btn_layout.add_widget(save_btn)
        btn_layout.add_widget(cancel_btn)
        root_layout.add_widget(btn_layout)

        self.add_widget(root_layout)

        # Inicializa plugins
        self.refresh_plugins()

    def _make_row(self, left_widget=None, center_text="", right_widget=None):
        """
        Create a horizontally centered row with 3 columns:
        - left_widget: Checkbox or other widget, width: LEFT_WIDTH
        - center_text: Centered label, width: CENTER_WIDTH
        - right_widget: Button or other widget, width: RIGHT_WIDTH
        """
        layout = BoxLayout(orientation="horizontal", size_hint_y=None, height=self.ROW_HEIGHT)

        # flexible space on the sides to center the row
        layout.add_widget(Widget(size_hint_x=1))

        # left
        if left_widget is None:
            left_widget = Widget(size_hint=(None, 1), width=self.LEFT_WIDTH)
        else:
            left_widget.size_hint = (None, 1)
            left_widget.width = self.LEFT_WIDTH
        layout.add_widget(left_widget)

        # center
        lbl = Label(text=center_text, size_hint=(None, 1), width=self.CENTER_WIDTH,
                    halign="center", valign="middle")
        lbl.bind(size=lbl.setter("text_size"))
        layout.add_widget(lbl)

        # right
        if right_widget is None:
            right_widget = Widget(size_hint=(None, 1), width=self.RIGHT_WIDTH)
        else:
            right_widget.size_hint = (None, 1)
            right_widget.width = self.RIGHT_WIDTH
        layout.add_widget(right_widget)

        layout.add_widget(Widget(size_hint_x=1))  

        return {"layout": layout, "left": left_widget, "center": lbl, "right": right_widget}

    def refresh_plugins(self):
        """Refresh the plugins section using centered rows with a width of 50%."""
        self.plugin_container.clear_widgets()
        enabled_plugins = set(self.config_manager.get_enabled_plugins())
        self.plugin_widgets = {}

        for plugin_name, info in self.plugin_manager.available_plugins.items():
            # Settings Button
            btn = Button(text="Settings", disabled=True)
            try:
                temp_instance = info["class"](config_manager=self.config_manager, check_init=True)
                if hasattr(temp_instance, "_open_plugin_config_menu_"):
                    btn.disabled = False
                    def make_click(instance=temp_instance):
                        return lambda *_: instance._open_plugin_config_menu_(parent=self)
                    btn.bind(on_release=make_click())
            except Exception:
                pass

            row = self._make_row(
                left_widget=CheckBox(active=(plugin_name in enabled_plugins)),
                center_text=plugin_name,
                right_widget=btn
            )
            self.plugin_widgets[plugin_name] = {
                "checkbox": row["left"],
                "label": row["center"],
                "settings_btn": row["right"]
            }
            self.plugin_container.add_widget(row["layout"])

        # --- Install button at the bottom ---
        install_btn = Button(text="Install Plugin", size_hint=(None, 1), width=self.CENTER_WIDTH)
        install_btn.bind(on_release=self.install_plugin)

        # Center the button using a horizontal BoxLayout.
        install_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=self.ROW_HEIGHT)
        install_row.add_widget(Widget()) 
        install_row.add_widget(install_btn)
        install_row.add_widget(Widget()) 
        self.plugin_container.add_widget(install_row)

    def save_config(self, *_):
        """Save changes to the configuration and update PluginManager"""
        self.config_manager.set("dark_mode", str(self.dark_mode_cb.active))

        enabled = [name for name, widgets in self.plugin_widgets.items() if widgets["checkbox"].active]
        self.config_manager.set_enabled_plugins(enabled)

        for plugin_name in self.plugin_manager.get_plugins():
            self.plugin_manager.toggle_plugin(plugin_name, plugin_name in enabled)

        if self.manager:
            self.manager.current = "start_window"

    def install_plugin(self, *_):
        """Open the FileDialog to install the plugin and refresh the UI."""
        if hasattr(self.plugin_manager, "import_plugins"):
            self.plugin_manager.import_plugins(on_complete=self.refresh_plugins)
        else:
            popup = Popup(
                title="Install Plugin",
                content=Label(text="Plugin installation not implemented."),
                size_hint=(0.6, 0.4)
            )
            popup.open()

