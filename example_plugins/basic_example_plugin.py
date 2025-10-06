# -*- coding: utf-8 -*-
"""
Basic Example Plugin
--------------------
This is the simplest possible example of a plugin for your application.
It includes only the bare minimum required so that the PluginManager
can load it and display it in the Plugins menu.
"""

from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button


# ======================= Plugin =======================

class BasicExamplePlugin:
    """
    Minimal example plugin.
    It only shows a basic popup when executed.
    """

    # Unique name of the plugin
    # - You can use "/" in the name to group plugins into subfolders in the menu.
    #   Example: "Examples/Basic" → will appear inside the "Examples" submenu
    name = "Examples/Basic Plugin"

    def __init__(self, config_manager=None, plugin_manager=None, check_init=False):
        """
        Minimal plugin initialization.
        - config_manager: global configuration manager (optional).
        - plugin_manager: reference to the plugin manager (optional).
        - check_init: if True, skips full initialization (useful for quick checks).
        """
        self.config_manager = config_manager
        self.plugin_manager = plugin_manager

    # ---------------------- Menu functions ----------------------
    def get_functions(self):
        """
        Return the functions that will appear in the plugin's menu.
        - Each entry is a tuple: (display_text, function_to_call).
        """
        return [
            ("Show popup", self.show_popup)
        ]

    # ---------------------- Example action ----------------------
    def show_popup(self, editor_window=None):
        """
        Example action: shows a basic popup with a message.
        - editor_window: reference to the editor window (not used here).
        """
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        label = Label(text="Hello from Basic Plugin! 👋")
        btn = Button(text="OK", size_hint_y=None, height=40)

        layout.add_widget(label)
        layout.add_widget(btn)

        popup = Popup(title="Basic Plugin", content=layout, size_hint=(None, None), size=(300, 150))
        btn.bind(on_release=popup.dismiss)
        popup.open()


# ======================= Registration =======================
# This variable is required: the plugin manager uses it to load the plugin.
plugin_class = BasicExamplePlugin
