# app/themed_screen.py
from kivy.uix.screenmanager import Screen
from kivy.graphics import Rectangle, Color
from kivy.clock import Clock
from app.style_manager import style_manager

class ThemedScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self._init_bg, 0)

    def _init_bg(self, dt):
        style = style_manager.get_style()
        bg_color = style.get("window_background_color", (0.1, 0.1, 0.1, 1))

        with self.canvas.before:
            self.bg_color_instruction = Color(*bg_color)
            self.bg_rect = Rectangle(size=self.size, pos=self.pos)

        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        if hasattr(self, "bg_rect"):
            self.bg_rect.pos = self.pos
            self.bg_rect.size = self.size

    def set_background_color(self, rgba):
        """Cambia el color de fondo dinámicamente."""
        if hasattr(self, "bg_color_instruction"):
            self.bg_color_instruction.rgba = rgba

