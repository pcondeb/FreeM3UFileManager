# -*- coding: utf-8 -*-
"""
Import Examples Helper Plugin
-----------------------------
Displays example JSON structures for importing channels and groups.
"""

from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout


class ImportExamplesHelperPlugin:
    name = "Examples/Import Channels-Groups/JSON Examples"

    def __init__(self, config_manager=None, plugin_manager=None, check_init=False):
        self.config_manager = config_manager
        self.plugin_manager = plugin_manager

    # ---------------------- Menu ----------------------
    def get_functions(self):
        return [
            ("Show example: Channel list", self.show_channels_example_popup),
            ("Show example: Groups and subgroups", self.show_groups_example_popup),
        ]

    # ---------------------- Popup Helpers ----------------------
    def _show_popup(self, title, content_text):
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        text_box = TextInput(text=content_text, readonly=True, font_size=13)
        layout.add_widget(text_box)
        btn_close = Button(text="Close", size_hint_y=None, height=40)
        layout.add_widget(btn_close)

        popup = Popup(title=title, content=layout, size_hint=(0.9, 0.9))
        btn_close.bind(on_release=lambda *a: popup.dismiss())
        popup.open()

    # ---------------------- Example 1: Channel list ----------------------
    def show_channels_example_popup(self, *args):
        example_text = """\
Example 1: Import a list of channels
-----------------------------------
[
    {
        "name": "Documentary One",
        "url": "http://stream.example.com/docone.m3u8",
        "tvg-id": "docone",
        "tvg-logo": "http://logos.example.com/docone.png",
        "group-title": "",
        "country": "XX",
        "language": "English"
    },
    {
        "name": "Documentary Two",
        "url": "http://stream.example.com/doctwo.m3u8",
        "tvg-id": "doctwo",
        "tvg-logo": "http://logos.example.com/doctwo.png",
        "group-title": "",
        "country": "XX",
        "language": "English"
    }
]

This list will be added to the currently selected group.
The "group-title" field will be automatically updated with the full path.
"""
        self._show_popup("JSON Example: Channel List", example_text)

    # ---------------------- Example 2: Groups and subgroups ----------------------
    def show_groups_example_popup(self, *args):
        example_text = """\
Example 2: Import multiple groups with subgroups
------------------------------------------------
{
    "Sports Group": {
        "_channels": [
          {
            "name": "SuperSports 1",
            "url": "http://stream.example.com/supersports1.m3u8",
            "tvg-id": "supersports1",
            "tvg-logo": "http://logos.example.com/supersports1.png",
            "group-title": "Sports Group",
            "country": "XX",
            "language": "English"
          },
          {
            "name": "SuperSports 2",
            "url": "http://stream.example.com/supersports2.m3u8",
            "tvg-id": "supersports2",
            "tvg-logo": "http://logos.example.com/supersports2.png",
            "group-title": "Sports Group",
            "country": "XX",
            "language": "English"
          }
        ]
    },

    "News Group": {
        "_channels": [
          {
            "name": "Global News",
            "url": "http://stream.example.com/globalnews.m3u8",
            "tvg-id": "globalnews",
            "tvg-logo": "http://logos.example.com/globalnews.png",
            "group-title": "News Group",
            "country": "XX",
            "language": "English"
          },
          {
            "name": "Local News",
            "url": "http://stream.example.com/localnews.m3u8",
            "tvg-id": "localnews",
            "tvg-logo": "http://logos.example.com/localnews.png",
            "group-title": "News Group",
            "country": "XX",
            "language": "English"
          }
        ],
        "News Sub Group": {
          "_channels": [
            {
              "name": "Global News 2",
              "url": "http://stream.example.com/globalnews2.m3u8",
              "tvg-id": "globalnews2",
              "tvg-logo": "http://logos.example.com/globalnews2.png",
              "group-title": "News Group/News Sub Group",
              "country": "XX",
              "language": "English"
            },
            {
              "name": "Local News 2",
              "url": "http://stream.example.com/localnews2.m3u8",
              "tvg-id": "localnews2",
              "tvg-logo": "http://logos.example.com/localnews2.png",
              "group-title": "News Group/News Sub Group",
              "country": "XX",
              "language": "English"
            }
          ]
        }
    }
}

This structure will create multiple groups and subgroups.
Each "_channels" array defines the channels inside a group.
"""
        self._show_popup("JSON Example: Groups and Subgroups", example_text)


# ======================= Plugin Registration =======================
plugin_class = ImportExamplesHelperPlugin
