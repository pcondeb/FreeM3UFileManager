# -*- coding: utf-8 -*-
"""
Configuration-Only Example Plugin
---------------------------------
This plugin demonstrates how to provide plugin-specific settings
that can be loaded, edited, and saved. It does not implement
any other plugin actions except configuration.
"""

from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput


# ======================= Utility function =======================

def popup_message(title, text):
    """
    Simple popup with a message and an OK button.
    Can be reused by other plugins.
    """
    layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
    label = Label(text=text)
    btn = Button(text='OK', size_hint_y=None, height=40)
    layout.add_widget(label)
    layout.add_widget(btn)
    popup = Popup(title=title, content=layout, size_hint=(None, None), size=(400, 200))
    btn.bind(on_release=popup.dismiss)
    popup.open()


# ======================= Plugin =======================

class ConfigExamplePlugin:
    """
    Configuration-only plugin example.
    - Minimal plugin for the PluginManager.
    - Provides a dedicated configuration menu.
    """

    # Unique plugin name.
    # You can use "/" in the name to group plugins in submenus.
    name = "Examples/Config Only Plugin"

    def __init__(self, config_manager=None, plugin_manager=None, check_init=False):
        """
        Plugin initialization.
        - config_manager: reference to the global configuration manager (optional)
        - plugin_manager: reference to the plugin manager (optional)
        - check_init: if True, skips full initialization
        """
        self.config_manager = config_manager
        self.plugin_manager = plugin_manager

        # Plugin-specific configuration variables
        self.some_path = "default_path"
        self.some_option = False

        # Load saved configuration if available
        self._load_config()

        if check_init:
            return

    # ---------------------- Configuration methods ----------------------
    def _load_config(self):
        """
        Load saved configuration for this plugin from the global config manager.
        """
        if not self.config_manager:
            return
        plugin_cfg_key = f"plugin_{self.name.replace('/', '_')}"
        self.some_path = self.config_manager.get("some_path", "default_path", section=plugin_cfg_key)
        self.some_option = self.config_manager.get("some_option", False, section=plugin_cfg_key)

    def _save_config(self):
        """
        Save current plugin configuration to the global config manager.
        """
        if not self.config_manager:
            return
        plugin_cfg_key = f"plugin_{self.name.replace('/', '_')}"
        self.config_manager.set("some_path", self.some_path, section=plugin_cfg_key)
        self.config_manager.set("some_option", self.some_option, section=plugin_cfg_key)
        try:
            self.config_manager.save()
            popup_message("Settings", "Plugin configuration saved successfully.")
        except Exception:
            pass

    # ---------------------- Menu functions ----------------------
    def get_functions(self):
        """
        Return the functions that will appear in the plugin's menu.
        - Only configuration function is provided.
        """
        return [
            # The "_open_plugin_config_menu_" function name is reserved
            # for the PluginManager to recognize as the configuration menu of the plugin.
            ("Open config", self._open_plugin_config_menu_)
        ]

    # ---------------------- Configuration menu ----------------------
    def _open_plugin_config_menu_(self, parent=None):
        """
        Opens a popup to edit the plugin's configuration.
        - This function is recognized by the PluginManager as the plugin's settings menu.
        """
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Path setting
        layout.add_widget(Label(text="Working Path:", height=50))
        path_input = TextInput(text=self.some_path, multiline=False)
        layout.add_widget(path_input)

        # Extra option setting
        layout.add_widget(Label(text="Extra option (free text):", height=50))
        opt_input = TextInput(text=str(self.some_option), multiline=False)
        layout.add_widget(opt_input)

        # Buttons layout
        btn_layout = BoxLayout(size_hint_y=None, height=50, spacing=5)
        btn_save = Button(text="Save")
        btn_cancel = Button(text="Cancel")
        btn_layout.add_widget(btn_save)
        btn_layout.add_widget(btn_cancel)
        layout.add_widget(btn_layout)

        popup = Popup(title="Config Only Plugin Settings",
                      content=layout, size_hint=(None, None), size=(700, 350))

        def save_and_close(*args):
            self.some_path = path_input.text.strip()
            self.some_option = opt_input.text.strip()
            self._save_config()
            popup.dismiss()

        btn_save.bind(on_release=save_and_close)
        btn_cancel.bind(on_release=popup.dismiss)
        popup.open()


# ======================= Registration =======================
# This variable is required: the plugin manager uses it to load the plugin.
plugin_class = ConfigExamplePlugin

