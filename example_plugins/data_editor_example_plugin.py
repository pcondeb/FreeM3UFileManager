# -*- coding: utf-8 -*-
"""
Data Editor Example Plugin
--------------------------
This plugin demonstrates how to edit a specific field in multiple selected items.
It shows a popup with:
- A dropdown (Spinner) to choose which field to modify.
- A TextInput to type the new value (can be empty).
- Accept and Cancel buttons.

When you click "Accept", it updates the selected channels/groups with the new value.
"""

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button


# ======================================================
#                   Helper Function
# ======================================================

def popup_message(title, text):
    """
    Utility popup for showing messages (info, success, errors).
    """
    layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
    label = Label(text=text)
    btn = Button(text="OK", size_hint_y=None, height=40)
    layout.add_widget(label)
    layout.add_widget(btn)
    popup = Popup(title=title, content=layout, size_hint=(None, None), size=(400, 200))
    btn.bind(on_release=popup.dismiss)
    popup.open()


# ======================================================
#                   Plugin Class
# ======================================================

class DataEditorExamplePlugin:
    """
    Example plugin for editing multiple channels' or groups' fields.
    """

    # This name determines how the plugin appears in the Plugins menu
    # You can use "/" to group plugins in submenus.
    name = "Examples/Data Editor Example Plugin"

    def __init__(self, config_manager=None, plugin_manager=None, check_init=False):
        self.config_manager = config_manager
        self.plugin_manager = plugin_manager

    # ---------------------- Plugin Menu ----------------------
    def get_functions(self):
        """
        Returns the plugin functions available in the menu.
        """
        return [
            ("Edit field for selected items", self.open_editor_popup)
        ]

    # ---------------------- Main Popup ----------------------
    def open_editor_popup(self, editor_window=None):
        """
        Opens a popup to select a field and enter a new value.
        """
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Available editable fields (you can expand this list)
        editable_fields = [
            "name",
            "url",
            "tvg-id",
            "tvg-name",
            "tvg-logo",
            "group-title",
            "radio",
            "tvg-shift"
        ]

        layout.add_widget(Label(text="Select field to edit:"))
        field_spinner = Spinner(text=editable_fields[0], values=editable_fields)
        layout.add_widget(field_spinner)

        layout.add_widget(Label(text="New value (leave empty to clear):"))
        value_input = TextInput(multiline=False)
        layout.add_widget(value_input)

        btn_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        btn_accept = Button(text="Accept")
        btn_cancel = Button(text="Cancel")
        btn_layout.add_widget(btn_accept)
        btn_layout.add_widget(btn_cancel)
        layout.add_widget(btn_layout)

        popup = Popup(
            title="Edit Data Field",
            content=layout,
            size_hint=(None, None),
            size=(400, 300),
            auto_dismiss=False
        )

        # Bind buttons
        btn_cancel.bind(on_release=popup.dismiss)
        btn_accept.bind(
            on_release=lambda x: (
                self.apply_field_change(
                    editor_window,
                    field_spinner.text,
                    value_input.text.strip()
                ),
                popup.dismiss()
            )
        )

        popup.open()

    # ---------------------- Apply Change ----------------------
    def apply_field_change(self, editor_window, field_name, new_value):
        """
        Applies the change to all selected items in the editor.
        """
        if not editor_window or not hasattr(editor_window, "editor_helper"):
            popup_message("Error", "Editor window not available.")
            return

        selected_items = [
            i for i in editor_window.editor_helper.items if getattr(i, "selected", False)
        ]

        if not selected_items:
            popup_message("No selection", "Please select at least one item.")
            return

        updated = 0

        # Helper to apply a field to a node (dict or list)
        def apply_to_node(node):
            nonlocal updated
            if isinstance(node, dict):
                node[field_name] = new_value
                updated += 1
            elif isinstance(node, list):
                for ch in node:
                    if isinstance(ch, dict):
                        ch[field_name] = new_value
                        updated += 1

        # Helper to locate real data in editor_window.data by path
        def find_real_node(data_ref, key_path):
            ref = data_ref
            for k in key_path:
                if isinstance(ref, dict):
                    ref = ref.get(k)
                else:
                    return None
            return ref

        for item in selected_items:
            node = getattr(item, "node", None)
            if not node:
                continue

            # Case 1: node is a unique ID string
            if isinstance(node, str):
                parent_node = find_real_node(editor_window.data, editor_window.editor_helper.current_path)
                if parent_node and "_channels" in parent_node:
                    for ch in parent_node["_channels"]:
                        if ch.get("_unique_id") == node:
                            apply_to_node(ch)

            # Case 2: node is a group dictionary
            elif isinstance(node, dict) and "key" in node:
                key_path = editor_window.editor_helper.current_path + [node["key"]]
                real_node = find_real_node(editor_window.data, key_path)
                if real_node:
                    apply_to_node(real_node.get("_channels", []))

            # Case 3: node is a channel dictionary
            elif isinstance(node, dict):
                parent_node = find_real_node(editor_window.data, editor_window.editor_helper.current_path)
                if parent_node and "_channels" in parent_node:
                    for ch in parent_node["_channels"]:
                        if ch is node or ch.get("name") == node.get("name"):
                            apply_to_node(ch)

        # Refresh editor and show results
        if updated > 0:
            try:
                editor_window.editor_helper.populate_list()
            except Exception:
                pass
            popup_message("Success", f"Updated {updated} items (field '{field_name}')")
        else:
            popup_message("No changes", "Nothing was updated.")


# ======================================================
#                   Plugin Registration
# ======================================================

plugin_class = DataEditorExamplePlugin
