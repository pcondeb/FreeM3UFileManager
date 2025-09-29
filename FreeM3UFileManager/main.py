# main.py
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from app.start_window import StartWindow
from app.config_manager import ConfigWindow

# --- Window Config ---
Window.size = (1600, 800) 
Window.minimum_width = 1100      
Window.minimum_height = 700

class M3UManagerApp(App):

    def build(self):
        self.title = "M3U List Manager"
        sm = ScreenManager()

        sm.add_widget(StartWindow(name="start_window"))

        return sm

if __name__ == "__main__": 
    M3UManagerApp().run()