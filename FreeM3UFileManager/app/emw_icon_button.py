# app/emw_icon_button.py
# -*- coding: utf-8 -*-

from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.image import Image
from kivy.graphics import Color, Rectangle



class IconButton(ButtonBehavior, AnchorLayout):
    """Botón con PNG como icono y background coloreable"""
    def __init__(self, icon_path, **kwargs):
        super().__init__(anchor_x='center', anchor_y='center', **kwargs)
        self.size_hint_y = None
        self.height = 50
        self.icon_path = icon_path

        # canvas para background
        with self.canvas.before:
            self.bg_color = Color(0.2, 0.2, 0.2, 1)  # default
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)

        # imagen del icono
        self.icon = Image(
            source=icon_path,
            size_hint=(None, None),
            size=(50, 50)
        )
        self.add_widget(self.icon)

    def _update_rect(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def set_background_color(self, rgba):
        self.bg_color.rgba = rgba

    def set_icon_color(self, rgba):
        self.icon.color = rgba