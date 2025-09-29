# app/style_manager.py
# -*- coding: utf-8 -*-
from kivy.core.text import LabelBase

class StyleManager:
    def __init__(self):
        try:
            LabelBase.register(name="DefaultFont", fn_regular="segoeuisymbol.ttf")
            default_font = "DefaultFont"
        except Exception:
            default_font = None

        self.styles = {
            "light": {
                "window_background_color": (0.8, 0.8, 0.8, 1),
                "background": (0.6, 0.6, 0.6, 1),  # #222222
                "foreground": (0.87, 0.87, 0.87, 1),  # #DDDDDD
                "button": {
                    "background_normal": (0.2, 0.2, 0.2, 1),  # #333333
                    "background_down": (0.0, 0.27, 0.4, 1),  # #004466
                    "text_color": (0.0, 1.0, 1.0, 1),        # #00FFFF
                    "font_size": 18,
                    "font_name": default_font,
                },
                "label": {
                    "font_size": 28,
                    "font_name": default_font,
                    "color": (0.87, 0.87, 1, 1),
                }
            },
            "dark":  {
                "window_background_color": (0.1, 0.1, 0.1, 1),
                "background": (0.3, 0.3, 0.3, 1),  # #DDDDDD
                "foreground": (0.13, 0.13, 0.13, 1),  # #222222
                "button": {
                    "background_normal": (0.93, 0.93, 0.93, 1),  # #EEEEEE
                    "background_down": (0.8, 0.8, 0.8, 1),      # #CCCCCC
                    "text_color": (0.0, 0.27, 0.4, 1),          # #004466
                    "font_size": 18,
                    "font_name": default_font,
                },
                "label": {
                    "font_size": 28,
                    "font_name": default_font,
                    "color": (0.73, 0.73, 0.95, 1),
                }
            },
        }
        self.current = "light"

    def get_style(self):
        return self.styles[self.current]

    def set_style(self, dark):
        if dark:
            self.current = "dark"
        else:
            self.current = "light"


# singleton
style_manager = StyleManager()
