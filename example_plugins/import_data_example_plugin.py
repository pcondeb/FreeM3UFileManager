# -*- coding: utf-8 -*-
"""
Import Data Example Plugin
--------------------------
Imports JSON data (channels or group structures) from user input text.
"""

from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from copy import deepcopy
import json

class ImportDataExamplePlugin:
    # Updated plugin path
    name = "Examples/Import Channels-Groups/Import Data Example"

    def __init__(self, config_manager=None, plugin_manager=None, check_init=False):
        self.config_manager = config_manager
        self.plugin_manager = plugin_manager

    # ---------------------- Menu ----------------------
    def get_functions(self):
        return [("Import data from JSON text", self.open_import_popup)]

    # ---------------------- Popup ----------------------
    def open_import_popup(self, editor_window=None):
        if editor_window is None:
            self._show_error("Editor reference not received.")
            return

        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)
        layout.add_widget(Label(text="Paste your JSON data below:"))
        text_input = TextInput(multiline=True, size_hint_y=1)
        layout.add_widget(text_input)

        # Buttons
        btn_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        btn_ok = Button(text="Accept")
        btn_cancel = Button(text="Cancel")

        btn_layout.add_widget(btn_ok)
        btn_layout.add_widget(btn_cancel)
        layout.add_widget(btn_layout)

        popup = Popup(title="Import JSON Data", content=layout, size_hint=(0.9, 0.9))
        btn_ok.bind(on_release=lambda *a: self._on_accept_import(popup, text_input, editor_window))
        btn_cancel.bind(on_release=lambda *a: popup.dismiss())
        popup.open()

    # ---------------------- Import Logic ----------------------
    def _on_accept_import(self, popup, text_input, editor_window):
        try:
            raw_text = text_input.text.strip()
            if not raw_text:
                self._show_error("No data provided.")
                return

            imported_data = json.loads(raw_text)
            eh = editor_window.editor_helper
            root_data = editor_window.data

            # Obtener grupo actual
            current_group = eh.get_current_data()
            current_path = eh.current_path
            group_title = "/".join(current_path) if current_path else ""

            # Importar lista de canales
            if isinstance(imported_data, list):
                for ch in imported_data:
                    if isinstance(ch, dict):
                        ch["group-title"] = group_title

                if "_channels" not in current_group:
                    current_group["_channels"] = []
                current_group["_channels"].extend(imported_data)

                self._show_info(f"✅ {len(imported_data)} channels added to group '{group_title or 'Root'}'.")

            # Importar grupos
            elif isinstance(imported_data, dict):
                for group_name, group_data in imported_data.items():
                    if group_name in current_group:
                        if isinstance(current_group[group_name], dict) and isinstance(group_data, dict):
                            current_group[group_name].update(deepcopy(group_data))
                        else:
                            suffix = 1
                            new_name = f"{group_name}_{suffix}"
                            while new_name in current_group:
                                suffix += 1
                                new_name = f"{group_name}_{suffix}"
                            current_group[new_name] = deepcopy(group_data)
                    else:
                        current_group[group_name] = deepcopy(group_data)

                from app.emw_items_utils import update_group_title_recursive
                update_group_title_recursive(root_data, [])

                self._show_info(f"✅ Groups imported into '{group_title or 'Root'}' successfully.")

            else:
                self._show_error("Invalid JSON format. Must be a list of channels or a group dictionary.")
                return

            popup.dismiss()
            eh.populate_list()

        except Exception as e:
            self._show_error(f"Could not import data:\n{e}")

    # ---------------------- Helper Popups ----------------------
    def _show_info(self, message):
        self._show_popup("Information", message)

    def _show_error(self, message):
        self._show_popup("Error", message)

    def _show_popup(self, title, message):
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        layout.add_widget(Label(text=message))
        btn = Button(text="OK", size_hint_y=None, height=40)
        layout.add_widget(btn)
        popup = Popup(title=title, content=layout, size_hint=(0.8, 0.4))
        btn.bind(on_release=lambda *a: popup.dismiss())
        popup.open()


# ======================= Plugin Registration =======================
plugin_class = ImportDataExamplePlugin
