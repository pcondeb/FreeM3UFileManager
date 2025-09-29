# app/editor_main_window.py
# -*- coding: utf-8 -*-
import os
import json
import re
import copy
from functools import partial

from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.button import Button
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle

from app.themed_screen import ThemedScreen
from app.editor_custom_listitems import EditorCustomQListItems
from app.add_channel_dialog import AddChannelDialog
from app.group_selector import GroupSelector
from app.dropdown_menu_popup import DropDownMenuPopup
from app.style_manager import style_manager
from app.emw_icon_button import IconButton
from app.file_dialog import FileDialog
from app.emw_file_utils import *
from app.emw_items_utils import (
    add_channel, add_group,
    remove_channel, remove_group,
    remove_channel_recursive, remove_group_recursive,
    collect_items, select_destination_group,
    copy_items, move_items,
    update_group_title_recursive
)


class EditorMainWindow(ThemedScreen):
    def __init__(self, file_path, is_new, config, plugin_manager, **kwargs):
        super().__init__(**kwargs)
        self.name = "editor"
        self.file_path = file_path
        self.is_new = is_new
        self.config = config
        self.plugin_manager = plugin_manager

        # dark mode control
        self.dark_mode = self.config.get_bool("dark_mode", True) if self.config else True
        style_manager.set_style(self.dark_mode)
        self.style = style_manager.get_style()

        # data load
        self.data = load_file(self.file_path, is_new)

        # UI main container
        self.main_layout = BoxLayout(spacing=5, padding=5)
        self.add_widget(self.main_layout)

        # Build UI
        self.setup_ui()

        # Apply theme
        with self.canvas.before:
            self.set_theme()

        # Optimización resize
        self._resize_event = None
        Window.bind(on_resize=self.on_window_resize)

    # -----------------------
    # Resize Window
    # -----------------------
    def on_window_resize(self, window, width, height):
        if self._resize_event:
            self._resize_event.cancel()
        self._resize_event = Clock.schedule_once(self.finish_resize, 0.3)

    def finish_resize(self, *args):
        self.update_layout_orientation()
        self.set_theme()
        if hasattr(self, "editor_helper"):
            self.editor_helper.populate_list()

    def update_layout_orientation(self):
        """Reorganiza layout según orientación de ventana"""
        self.main_layout.clear_widgets()

        top_buttons_list = [self.add_btn, self.remove_btn, self.copy_move_btn, self.select_menu_btn, self.move_items_up_btn, self.move_items_down_btn]
        bottom_buttons_list = [self.toggle_theme_btn, self.plugins_btn, self.import_btn, self.save_btn]

        for btn in top_buttons_list + bottom_buttons_list:
            if btn.parent:
                btn.parent.remove_widget(btn)

        if Window.width > Window.height:  # Horizontal → botones a la derecha
            self.main_layout.orientation = "horizontal"
            self.scroll.size_hint = (0.95, 1)
            self.main_layout.add_widget(self.scroll)

            self.button_panel.clear_widgets()
            self.button_panel.orientation = "vertical"
            self.button_panel.size_hint = (0.05, 1)

            top_panel = AnchorLayout(anchor_x='center', anchor_y='top')
            top_box = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None)
            for btn in top_buttons_list:
                top_box.add_widget(btn)
            top_box.height = sum(btn.height + top_box.spacing for btn in top_buttons_list)
            top_panel.add_widget(top_box)

            bottom_panel = AnchorLayout(anchor_x='center', anchor_y='bottom')
            bottom_box = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None)
            for btn in bottom_buttons_list:
                bottom_box.add_widget(btn)
            bottom_box.height = sum(btn.height + bottom_box.spacing for btn in bottom_buttons_list)
            bottom_panel.add_widget(bottom_box)

            self.button_panel.add_widget(top_panel)
            self.button_panel.add_widget(bottom_panel)
            self.main_layout.add_widget(self.button_panel)

        else:  # Vertical → botones abajo
            self.main_layout.orientation = "vertical"
            self.scroll.size_hint = (1, 0.9)
            self.main_layout.add_widget(self.scroll)

            self.button_panel.clear_widgets()
            self.button_panel.orientation = "horizontal"
            self.button_panel.size_hint = (1, 0.1)

            for btn in top_buttons_list + bottom_buttons_list:
                self.button_panel.add_widget(btn)
            self.main_layout.add_widget(self.button_panel)

    # -----------------------
    # Theme
    # -----------------------
    def set_theme(self):
        self.style = style_manager.get_style()
        bg_color = self.style.get("window_background_color", (0.1, 0.1, 0.1, 1))
        self.set_background_color(bg_color)

        text_color = self.style["button"].get("text_color", (1, 1, 1, 1))
        btn_bg = self.style["button"].get("background_normal", (0.2, 0.2, 0.2, 1))

        for btn in [self.add_btn, self.remove_btn, self.copy_move_btn, self.select_menu_btn, self.move_items_up_btn, self.move_items_down_btn,
                    self.toggle_theme_btn, self.plugins_btn, self.import_btn, self.save_btn]:
            btn.set_background_color(btn_bg)
            btn.set_icon_color(text_color)

        self.editor_helper.style = self.style
        self.editor_helper.populate_list()

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        style_manager.set_style(self.dark_mode)
        self.set_theme()

    # -----------------------
    # UI
    # -----------------------
    def setup_ui(self):
        self.scroll = ScrollView()
        self.list_content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
        self.list_content.bind(minimum_height=self.list_content.setter('height'))
        self.scroll.add_widget(self.list_content)

        self.button_panel = BoxLayout(spacing=5, padding=5)

        # Build buttons with icons
        self.add_btn = IconButton("app/icons/add.png")
        self.remove_btn = IconButton("app/icons/remove.png")
        self.copy_move_btn = IconButton("app/icons/copy.png")
        self.select_menu_btn = IconButton("app/icons/select.png")
        self.move_items_up_btn = IconButton("app/icons/icon_up.png")
        self.move_items_down_btn = IconButton("app/icons/icon_down.png")
        #self.print_btn = IconButton("app/icons/icon_down.png")
        self.toggle_theme_btn = IconButton("app/icons/theme.png")
        self.plugins_btn = IconButton("app/icons/plugins.png")
        self.import_btn = IconButton("app/icons/import.png")
        self.save_btn = IconButton("app/icons/save.png")

        # Assign callbacks
        self.add_btn.bind(on_release=lambda x: self.add_popup())
        self.remove_btn.bind(on_release=lambda x: self.delete_selected())
        self.copy_move_btn.bind(on_release=lambda x: self.open_copy_move_menu())
        self.select_menu_btn.bind(on_release=lambda x: self.select_dialog())
        self.move_items_up_btn.bind(on_release=lambda x: self.reorder_selected_items("up"))
        self.move_items_down_btn.bind(on_release=lambda x: self.reorder_selected_items("down"))
        #self.print_btn.bind(on_release=lambda x: self.print_json_data())

        self.toggle_theme_btn.bind(on_release=lambda x: self.toggle_theme())
        self.plugins_btn.bind(on_release=lambda x: self.open_plugins_menu())
        self.import_btn.bind(on_release=lambda x: self.import_dialog())
        self.save_btn.bind(on_release=lambda x: self.save_btn_action())

        self.top_buttons = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None)
        for btn in [self.add_btn, self.remove_btn, self.copy_move_btn, self.select_menu_btn, self.move_items_up_btn, self.move_items_down_btn]:
            btn.height = 60
            self.top_buttons.add_widget(btn)

        self.bottom_buttons = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None)
        for btn in [self.toggle_theme_btn, self.plugins_btn, self.import_btn, self.save_btn]:
            btn.height = 60
            self.bottom_buttons.add_widget(btn)

        self.update_layout_orientation()

        self.editor_helper = EditorCustomQListItems(
            container=self.list_content,
            style=self.style,
            parent=self
        )
        self.editor_helper.load_data(self.data)


    # -----------------------
    # Popups
    # -----------------------
    def show_popup(self, title, message):
        popup = Popup(
            title=title,
            content=Label(text=message),
            size_hint=(0.4, 0.3)
        )
        popup.open()

    def add_popup(self):
        content = BoxLayout(orientation="vertical", spacing=10, padding=10)
        spinner = Spinner(text="Group", values=["Group", "Channel"], size_hint_y=None, height=60)
        content.add_widget(Label(text="Select type:"))
        content.add_widget(spinner)
        btn_layout = BoxLayout(size_hint_y=None, height=40, spacing=5)
        ok_btn = Button(text="OK")
        cancel_btn = Button(text="Cancel")
        btn_layout.add_widget(ok_btn)
        btn_layout.add_widget(cancel_btn)
        content.add_widget(btn_layout)

        popup = Popup(title="Add Item", content=content, size_hint=(0.4, 0.5))
        ok_btn.bind(on_release=lambda x: self._on_add_popup_ok(spinner.text, popup))
        cancel_btn.bind(on_release=lambda x: popup.dismiss())
        popup.open()

    def _on_add_popup_ok(self, choice, popup):
        popup.dismiss()
        if choice == "Channel":
            add_channel(self.editor_helper)
        else:
            add_group(self.editor_helper)

    def delete_selected(self):
        selected_items = [item for item in self.editor_helper.items if item.selected]
        if not selected_items:
            self.show_popup("Notice", "No items selected.")
            return

        for item in selected_items:
            data = item.data
            if data.get("item_type") == "channel":
                remove_channel(self.editor_helper, data)
            elif data.get("item_type") == "group":
                remove_group(self.editor_helper, data.get("key"))
        self.editor_helper.populate_list()


    def reorder_selected_items(self, direction="up"):
        """
        Reorder the selected elements (channels or groups) within the current level as a block, while maintaining their relative order.
        direction = "up" or "down"
        """
        selected_items = [item for item in self.editor_helper.items if item.selected]
        if not selected_items:
            self.show_popup("Notice", "No items selected.")
            return

        current_data = self.editor_helper.get_current_data()

        # --- CHANNELS ---
        if isinstance(current_data, dict) and "_channels" in current_data:
            channels = current_data["_channels"]

            # locate indices of selected items
            selected_indices = [
                i for i, ch in enumerate(channels)
                if any(ch.get("_unique_id") == item.data.get("_unique_id") for item in selected_items if item.data.get("item_type") == "channel")
            ]
            if selected_indices:
                if direction == "up":
                    if min(selected_indices) > 0:
                        for i in selected_indices:
                            channels[i - 1], channels[i] = channels[i], channels[i - 1]
                elif direction == "down":
                    if max(selected_indices) < len(channels) - 1:
                        for i in reversed(selected_indices):
                            channels[i + 1], channels[i] = channels[i], channels[i + 1]

        # --- GROUPS ---
        if isinstance(current_data, dict):
            keys = list(current_data.keys())
            # remove _channels because it's not a group
            if "_channels" in keys:
                keys.remove("_channels")

            selected_keys = [
                item.data.get("key")
                for item in selected_items if item.data.get("item_type") == "group"
            ]
            selected_indices = [i for i, k in enumerate(keys) if k in selected_keys]

            if selected_indices:
                if direction == "up":
                    if min(selected_indices) > 0:
                        for i in selected_indices:
                            keys[i - 1], keys[i] = keys[i], keys[i - 1]
                elif direction == "down":
                    if max(selected_indices) < len(keys) - 1:
                        for i in reversed(selected_indices):
                            keys[i + 1], keys[i] = keys[i], keys[i + 1]

                # rebuild dictionary with new order
                reordered = {}
                if "_channels" in current_data:  # # keep the channels clear first
                    reordered["_channels"] = current_data["_channels"]
                for k in keys:
                    reordered[k] = current_data[k]

                current_data.clear()
                current_data.update(reordered)

        self.editor_helper.populate_list()

    def _move_channel(self, current_data, channel_data, direction):
        """
        Move a channel in the _channels list of current_data.
        """
        if not isinstance(current_data, dict):
            return
        channels = current_data.get("_channels")
        if not isinstance(channels, list):
            return

        # localizar índice
        idx = None
        for i, ch in enumerate(channels):
            if ch is channel_data or (
                isinstance(ch, dict) and ch.get("_unique_id") == channel_data.get("_unique_id")
            ):
                idx = i
                break

        if idx is None:
            return

        # mover
        if direction == "up" and idx > 0:
            channels[idx - 1], channels[idx] = channels[idx], channels[idx - 1]
        elif direction == "down" and idx < len(channels) - 1:
            channels[idx + 1], channels[idx] = channels[idx], channels[idx + 1]

    def _move_group(self, current_data, group_key, direction):
        """
        Move a group within the current_data dictionary.
        """
        if not isinstance(current_data, dict) or not group_key in current_data:
            return

        keys = list(current_data.keys())
        idx = keys.index(group_key)

        if direction == "up" and idx > 0:
            keys[idx - 1], keys[idx] = keys[idx], keys[idx - 1]
        elif direction == "down" and idx < len(keys) - 1:
            keys[idx + 1], keys[idx] = keys[idx], keys[idx + 1]
        else:
            return

        # rebuild the dictionary in the new order
        reordered = {k: current_data[k] for k in keys}
        current_data.clear()
        current_data.update(reordered)


    def open_copy_move_menu(self):
        menu_dict = {
                "Copy": lambda: copy_items(self.editor_helper, self),
                "Move": lambda: move_items(self.editor_helper, self),
            }
        DropDownMenuPopup(menu_dict, title="Plugins").open()


    # -----------------------
    # Plugins
    # -----------------------
    def open_plugins_menu(self):
        menu_dict = self.populate_plugins_structure(self.plugin_manager, parent_instance=self)
        DropDownMenuPopup(menu_dict, title="Plugins").open()

    def populate_plugins_structure(self, plugin_manager, parent_instance=None):
        """
        This function builds the dictionary structure required for the DropDownMenuPopup
        based on the plugins registered with the plugin manager.
        Submenus are created using '/' as a separator in both the plugin name and the function name.

        It returns a dictionary in the format {name: callback | sub-dictionary}.
        """
        menu_structure = {}
        submenus_cache = {}  # key: full path -> sub-dictionary

        for plugin_name, plugin_data in plugin_manager.get_plugins().items():
            # Create the submenu path based on the plugin name
            parts = plugin_name.split("/")
            path_so_far = ""
            parent_dict = menu_structure

            for part in parts:
                path_so_far = f"{path_so_far}/{part}" if path_so_far else part
                if path_so_far not in submenus_cache:
                    submenus_cache[path_so_far] = {}
                    parent_dict[part] = submenus_cache[path_so_far]
                parent_dict = submenus_cache[path_so_far]

            plugin_menu_dict = parent_dict

            # Plugin features
            for func_name, func_callback in plugin_data["instance"].get_functions():
                func_parts = func_name.split("/")
                func_path_so_far = plugin_name  # Initialize with plugin path
                parent_func_dict = plugin_menu_dict

                for part in func_parts[:-1]:
                    func_path_so_far = f"{func_path_so_far}/{part}"
                    if func_path_so_far not in submenus_cache:
                        submenus_cache[func_path_so_far] = {}
                        parent_func_dict[part] = submenus_cache[func_path_so_far]
                    parent_func_dict = submenus_cache[func_path_so_far]

                action_name = func_parts[-1]
                if parent_instance:
                    parent_func_dict[action_name] = partial(func_callback, parent_instance)
                else:
                    parent_func_dict[action_name] = func_callback

        return menu_structure


    def select_dialog(self):
        menu_dict = {
                "Select": {
                        "All Items": lambda: self.editor_helper.select_items(True, "all"),
                        "All Channels": lambda: self.editor_helper.select_items(True, "channel"),
                        "All Groups": lambda: self.editor_helper.select_items(True, "group"),
                    },
                "Unselect": {
                        "All Items": lambda: self.editor_helper.select_items(False, "all"),
                        "All Channels": lambda: self.editor_helper.select_items(False, "channel"),
                        "All Groups": lambda: self.editor_helper.select_items(False, "group"),
                    }
                 
            }
        DropDownMenuPopup(menu_dict, title="Select/Unselect items").open()

    # -----------------------
    # Import / Export
    # -----------------------
    def merge_data_with_recure_names(self, imported_data, current_data):
        """Merge sin sobrescribir grupos, añade sufijos si hay duplicados."""
        for group_name, group_channels in imported_data.items():
            if group_name not in current_data:
                current_data[group_name] = group_channels
            else:
                suffix = 1
                new_name = f"{group_name}_{suffix}"
                while new_name in current_data:
                    suffix += 1
                    new_name = f"{group_name}_{suffix}"
                current_data[new_name] = group_channels
        return current_data


    def import_dialog(self):
        """Use FileDialog to import correspondence without overwriting existing data."""
        def on_file_chosen(path):
            try:
                _, ext = os.path.splitext(path)
                ext = ext.lower()

                if ext == ".json":
                    with open(path, "r", encoding="utf-8") as f:
                        imported_data = json.load(f)

                elif ext == ".m3u" or ext == ".m3u8":
                    imported_data = load_file(path, is_new=False)

                else:
                    self.show_popup("Error", f"Unsupported file type: {ext}")
                    return

                if not isinstance(imported_data, dict):
                    self.show_popup("Error", "Invalid file structure.")
                    return

                current_data = self.editor_helper.get_current_data()
                if current_data is None:
                    current_data = {}

                # Merge without overwriting
                updated = self.merge_data_with_recure_names(imported_data, current_data)

                print(updated)

                # Save changes to the helper
                self.data = updated

                # Refresh list in the UI
                self.editor_helper.populate_list()

            except Exception as e:
                print(f"Error importing data: {e}")

        # Open the FileDialog in "open" mode
        file_dialog = FileDialog(mode="open", file_types=["*.m3u", "*.m3u8", "*.json"], callback=on_file_chosen)
        file_dialog.open()

    def save_btn_action(self, *args):
        def on_file_selected(full_path):
            # We obtain the filter from the dialog box that opened.
            selected_filter = file_dialog.filter_spinner.text if file_dialog.filter_spinner else "*.m3u"

            # check extension
            _, ext = os.path.splitext(full_path)
            if not ext:
                if selected_filter and selected_filter != "*.*":
                    ext = selected_filter.replace("*", "")
                    full_path += ext
                else:
                    ext = ".m3u"
                    full_path += ext

            try:
                if ext.lower() == ".m3u":
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write("#EXTM3U\n")
                        write_m3u_recursive(self.data, f)
                elif ext.lower() == ".json":
                    with open(full_path, "w", encoding="utf-8") as f:
                        json.dump(self.data, f, indent=4, ensure_ascii=False)
                else:
                    self.show_popup("Error", f"Unsupported extension: {ext}")
                    return

                self.show_popup("Success", f"File saved in:\n{full_path}")
            except Exception as e:
                self.show_popup("Error", str(e))

        # Create the dialogue
        file_dialog = FileDialog(
            mode="save",
            title="Save File",
            callback=on_file_selected,
            default_path=os.getcwd()
        )
        file_dialog.open()

    def export_m3u(self, out_file):
        """Export data in M3U format."""
        try:
            with open(out_file, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                write_m3u_recursive(self.data, f)

            self.config.set("last_file", out_file, "[GENERAL]")

            self.show_popup("Success", f"File saved to:\n{out_file}")
        except Exception as e:
            self.show_popup("Error", str(e))

    def export_json(self, out_file):
        """Export data in JSON format."""
        try:
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
            self.show_popup("Success", f"File saved to:\n{out_file}")
        except Exception as e:
            self.show_popup("Error", str(e))

    def print_json_data(self):
        print(json.dumps(self.data, indent=4, ensure_ascii=False))