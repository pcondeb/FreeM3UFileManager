# app/editor_custom_listitems.py
# -*- coding: utf-8 -*-
import string
from functools import partial
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import AsyncImage, Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.properties import BooleanProperty, ObjectProperty, StringProperty, ListProperty
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from app.add_channel_dialog import AddChannelDialog
from app.emw_items_utils import edit_channel, rename_group

ICON_PATH = "app/icons/"

FIELD_ICONS = {
    "radio": f"{ICON_PATH}radio.png",
    "tvg-id": f"{ICON_PATH}id.png",
    "tvg-logo": f"{ICON_PATH}logo.png",
    "tvg-country": f"{ICON_PATH}country.png",
    "tvg-language": f"{ICON_PATH}language.png",
    "tvg-url": f"{ICON_PATH}url.png",
    "tvg-rec": f"{ICON_PATH}rec.png",
    "tvg-chno": f"{ICON_PATH}chno.png",
    "url": f"{ICON_PATH}url.png",
}

class CustomListItem(BoxLayout):
    item_type = StringProperty("channel")  # "channel", "group", "back"
    selected = BooleanProperty(False)
    data = ObjectProperty(None)           # Copy of the data to display
    node = ObjectProperty(None)           # Reference to the original node (can be a dictionary)
    key_path = ListProperty([])           # Path inside editor_window.data

    def __init__(self, data=None, style=None, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=70, **kwargs)
        self.data = data or {}
        self.node = data                     # Original node that needs to be modified
        self.item_type = self.data.get("item_type", "channel")
        self.style = style or {}
        self.selected = False
        self.key_path = []                   

        # Internal widgets
        self.icon_widget = None
        self.text_label = None
        self.open_btn = None
        self.edit_btn = None
        self.count_label = None
        self.indicators_box = None

        self.build_ui()
        Clock.schedule_once(lambda dt: self._update_background(self.style))

    def build_ui(self):
        self.clear_widgets()

        # --- Main Icon ---
        if self.item_type == "channel":
            logo_url = self.data.get("tvg-logo") or self.data.get("logo")
            if logo_url:
                self.icon_widget = AsyncImage(source=logo_url, size_hint_x=None, width=70)
            else:
                self.icon_widget = Image(source=f"{ICON_PATH}channel.png", size_hint_x=None, width=70)
        elif self.item_type == "group":
            self.icon_widget = Image(source=f"{ICON_PATH}folder.png", size_hint_x=None, width=70)
        elif self.item_type == "back":
            self.icon_widget = Image(source=f"{ICON_PATH}back.png", size_hint_x=None, width=70)
        else:
            self.icon_widget = Image(source=f"{ICON_PATH}unknown.png", size_hint_x=None, width=70)
        self.add_widget(self.icon_widget)

        # --- Main text ---
        self.text_label = Label(text=self.data.get("name", "Unnamed"), halign="left", valign="middle")
        self.add_widget(self.text_label)

        # --- Group: counter + buttons ---
        if self.item_type == "group":
            children = self.data.get("children", {})
            channel_count = 0
            if isinstance(children, dict) and "_channels" in children:
                channel_count = len(children["_channels"])
            elif isinstance(children, list):
                channel_count = len(children)

            self.count_label = Label(text="Channels:"+str(channel_count)+"  ",  
                                     font_size=24, 
                                     color=self.style.get("label").get("color", (1, 1, 1, 1)),
                                     size_hint_x=None, 
                                     width=180)
            self.add_widget(self.count_label)

            self.edit_btn = BorderedIconButton(f"{ICON_PATH}edit.png", self.style)
            self.open_btn = BorderedIconButton(f"{ICON_PATH}open.png", self.style)
            self.add_widget(self.edit_btn)
            self.add_widget(self.open_btn)

        # --- Channel: indicators + edit ---
        elif self.item_type == "channel":
            self.indicators_box = BoxLayout(orientation="horizontal", size_hint_x=None, width=150)
            for field, icon_path in FIELD_ICONS.items():
                if self.data.get(field):
                    img = Image(source=icon_path, size_hint_x=None, width=24)
                    if field == "tvg-logo" and not self.data.get("logo_valid", True):
                        img.color = (1, 0, 0, 1)
                    self.indicators_box.add_widget(img)
            self.add_widget(self.indicators_box)

            self.edit_btn = BorderedIconButton(f"{ICON_PATH}edit.png", self.style)
            self.add_widget(self.edit_btn)

        self.apply_style(self.style)

    def apply_style(self, style):
        self.style = style
        label_style = style.get("label", {})

        if self.text_label:
            self.text_label.color = label_style.get("color", (1, 1, 1, 1))
            self.text_label.font_size = label_style.get("font_size", 16)

        button_style = style.get("label", {})

        self._update_background(style)

    def _update_background(self, style, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.selected:
                Color(0.3, 0.5, 0.9, 0.3)
            else:
                bg = style.get("background", (0.15, 0.15, 0.15, 1))
                Color(*bg)
            Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: self._update_background(self.style),
                  size=lambda *_: self._update_background(self.style))

    def set_selected(self, style, value):
        self.selected = value
        self._update_background(self.style)


class BorderedIconButton(BoxLayout):
    def __init__(self, icon_path, style, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.width = 70
        self.height = 70
        self.padding = 5

        # Fondo gris detrás
        with self.canvas.before:
            Color(*style.get("button").get("background_normal"))
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        # Botón con icono
        self.button = Button(
            background_normal=icon_path,
            background_down=icon_path,
            background_color=style.get("button").get("text_color"),
            border=(0, 0, 0, 0),
            size_hint=(.9, .9)
        )
        self.add_widget(self.button)

    def _update_bg(self, *args):
        margin = 5
        self.bg_rect.pos = (self.x + margin, self.y + margin)
        self.bg_rect.size = (self.width - 2*margin, self.height - 2*margin)


class EditorCustomQListItems:
    """Helper to populate a BoxLayout within a ScrollView with custom items from a JSON dictionary/list"""
    def __init__(self, container, style=None, parent=None):
        self.container = container
        self.parent = parent
        self.items = []
        self.data_root = {}
        self.current_path = []
        self.style = style or {}

    def set_style(self, style):
        """Change style at runtime"""
        self.style = style
        for item in self.items:
            item.apply_style(style)

    # -----------------------
    # Load and display data
    # -----------------------
    def load_data(self, data):
        self.data_root = data
        self.current_path = []
        self.populate_list()

    def get_current_data(self):
        ref = self.data_root
        for key in self.current_path:
            ref = ref.get(key, {})
        return ref

    def populate_list(self):
        # Save current selection
        selected_ids = {item.data.get("_unique_id") for item in self.items if item.selected}

        self.container.clear_widgets()
        self.items.clear()
        data = self.get_current_data()

        # --- Back ---
        if self.current_path:
            back_item = CustomListItem(
                data={"name": "Back", "item_type": "back", "_unique_id": "back", "_display_name": "Back"},
                style=self.style
            )
            back_item.bind(on_touch_down=lambda i, t: self.go_back() if back_item.collide_point(*t.pos) else False)
            # Back is never selected.
            self.items.append(back_item)
            self.container.add_widget(back_item)

        # --- Groups ---
        if isinstance(data, dict):
            for k, v in data.items():
                if k == "_channels":
                    continue
                group_data = {
                    "name": k,
                    "item_type": "group",
                    "children": v,
                    "key": k,
                    "_unique_id": f"{self.current_path}::{k}",
                    "_display_name": k
                }
                group_item = CustomListItem(data=group_data, style=self.style)
                # Restore selection
                if group_data["_unique_id"] in selected_ids:
                    group_item.set_selected(self.style, True)

                if group_item.open_btn:
                    group_item.open_btn.button.bind(on_release=lambda btn, gd=group_data: self.open_group(gd))
                    group_item.open_btn.button.bind(on_touch_down=self._on_item_touch)
                    
                if group_item.edit_btn:
                    group_item.edit_btn.button.bind(on_release=lambda btn, gd=group_data: rename_group(self, gd))
                    group_item.edit_btn.button.bind(on_touch_down=self._on_item_touch)

                self.items.append(group_item)
                self.container.add_widget(group_item)

        # --- Channels ---
        channels = []
        if isinstance(data, dict) and "_channels" in data:
            channels = data["_channels"]
        elif isinstance(data, list):
            channels = data

        for ch in channels:
            # Add identifiers and display name
            full_path = "::".join(self.current_path)
            ch["_unique_id"] = f'{full_path}::{ch.get("name","Unknown")}::{ch.get("url","")}'
            ch["_display_name"] = ch.get("name", "Unknown")

        for ch in channels:
            ch_item = CustomListItem(data={**ch, "item_type": "channel"}, style=self.style)
            # Restore selection
            if ch["_unique_id"] in selected_ids:
                ch_item.set_selected(self.style, True)

            if ch_item.edit_btn:
                ch_item.edit_btn.button.bind(on_release=lambda instance, ch=ch: edit_channel(self, ch))
            ch_item.bind(on_touch_down=self._on_item_touch)
            self.items.append(ch_item)
            self.container.add_widget(ch_item)

    # -----------------------
    # Navigation
    # -----------------------
    def open_group(self, group_data, _=None):
        self.current_path.append(group_data["key"])
        self.populate_list()

    def go_back(self):
        if self.current_path:
            self.current_path.pop()
            self.populate_list()

    # -----------------------
    # Selección
    # -----------------------
    def _on_item_touch(self, instance, touch):
        # If the instance is a child button, navigate up to the CustomListItem container.
        if not isinstance(instance, CustomListItem):
            instance = instance.parent
            while instance and not isinstance(instance, CustomListItem):
                instance = instance.parent
            if instance is None:
                return False

        if not instance.collide_point(*touch.pos):
            return False
        if getattr(instance, "open_btn", None) and instance.open_btn.collide_point(*touch.pos):
            return False
        if getattr(instance, "edit_btn", None) and instance.edit_btn.collide_point(*touch.pos):
            return False
        if instance.data.get("item_type") == "back":
            return False

        instance.set_selected(self.style, not instance.selected)
        return True

    def clear_selection(self):
        for item in self.items:
            item.set_selected(self.style, False)

    def get_selected_items(self):
        return [item.data for item in self.items if item.selected]

    def select_items(self, select_value=True, items_type="all"):
        for item in self.items:
            if item.item_type == "back":
                continue

            if items_type == "all":
                item.set_selected(self.style, select_value)
            else:
                if items_type == "channel" and item.item_type == "channel":
                    item.set_selected(self.style, select_value)
                if items_type == "group" and item.item_type == "group":
                    item.set_selected(self.style, select_value)

    # -----------------------
    # Data modification
    # -----------------------
    def add_item(self, data):
        """Add a new item (channel or group) while respecting the _unique_id and _display_name."""
        # Si es canal
        if data.get("item_type") == "channel":
            data["_unique_id"] = f'{data.get("name","Unknown")}::{data.get("url","")}'
            data["_display_name"] = data.get("name", "Unknown")
        # Si es grupo
        elif data.get("item_type") == "group":
            data["_unique_id"] = f'{self.current_path}::{data.get("name","Unnamed")}'
            data["_display_name"] = data.get("name","Unnamed")

        item = CustomListItem(data=data, style=self.style)
        item.bind(on_touch_down=self._on_item_touch)
        self.items.append(item)
        self.container.add_widget(item)

    def remove_item(self, data):
        to_remove = None
        for item in self.items:
            if item.data == data:
                to_remove = item
                break
        if to_remove:
            self.items.remove(to_remove)
            self.container.remove_widget(to_remove)

    def get_all_items_flat(self):
        return [item.data for item in self.items]
