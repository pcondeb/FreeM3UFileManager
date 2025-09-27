# app/file_dialog.py
# -*- coding: utf-8 -*-
import os, sys, json
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from app.paths_module import get_user_data_dir

RECENT_FILE = get_user_data_dir() / "recent_paths.json"

def get_default_locations():
    """Genera accesos rápidos según el sistema operativo."""
    home = os.path.expanduser("~")
    locations = {
        "Home": home,
        "Desktop": os.path.join(home, "Desktop"),
        "Documents": os.path.join(home, "Documents"),
        "Downloads": os.path.join(home, "Downloads"),
    }

    if sys.platform.startswith("win"):
        locations["C:"] = "C:\\"
        for d in "DEFGHIJKLMNOPQRSTUVWXYZ":
            drive = f"{d}:\\"
            if os.path.exists(drive):
                locations[drive] = drive
    else:
        for mount in ["/mnt", "/media", "/Volumes"]:
            if os.path.exists(mount):
                locations[os.path.basename(mount)] = mount

    return {k: v for k, v in locations.items() if os.path.exists(v)}

def load_recent_paths():
    """Carga historial de rutas recientes."""
    if os.path.exists(RECENT_FILE):
        try:
            with open(RECENT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_recent_path(path):
    """Guarda la ruta en el historial."""
    paths = load_recent_paths()
    default_locs = set(get_default_locations().values())
    if path in default_locs:
        return  # no guardar si es una ubicación principal
    if path in paths:
        paths.remove(path)
    paths.insert(0, path)
    paths = paths[:10]
    with open(RECENT_FILE, "w", encoding="utf-8") as f:
        json.dump(paths, f)

class FileDialog(Popup):
    def __init__(self, mode="open", file_types=["*.m3u", "*.json"], title="Select File", default_path="", callback=None, **kwargs):
        super().__init__(title=title, size_hint=(0.95, 0.95), **kwargs)
        self.mode = mode
        self.callback = callback
        self.file_types = file_types

        main_layout = BoxLayout(orientation="horizontal", spacing=5, padding=5)

        # --- Sidebar ---
        sidebar = BoxLayout(orientation="vertical", size_hint_x=0.25, spacing=5)

        sidebar.add_widget(Label(text="Ubicaciones", size_hint_y=None, height=30))
        default_locations = get_default_locations()
        for name, path in default_locations.items():
            btn = Button(text=name, size_hint_y=None, height=35)
            btn.bind(on_release=lambda b, p=path: self.change_dir(p))
            sidebar.add_widget(btn)

        sidebar.add_widget(Widget())  # espacio flexible

        recents = load_recent_paths()
        if recents:
            sidebar.add_widget(Label(text="Recientes", size_hint_y=None, height=30))
            for path in recents:
                if path in default_locations.values() or not os.path.exists(path):
                    continue
                display_text = path[-30:] if len(path) > 30 else path
                btn = Button(text=display_text, size_hint_y=None, height=35)
                btn.bind(on_release=lambda b, p=path: self.change_dir(p))
                sidebar.add_widget(btn)

        main_layout.add_widget(sidebar)

        # --- Layout central ---
        central_layout = BoxLayout(orientation="vertical", spacing=5)

        # Label con la ruta actual
        self.path_label = Label(
            text=default_path or os.getcwd(),
            size_hint_y=None,
            height=25,
            halign="left",
            valign="middle",
            shorten=True,
        )
        self.path_label.bind(size=lambda l, s: setattr(l, "text_size", (s[0], None)))
        central_layout.add_widget(self.path_label)

        # FileChooser
        self.filechooser = FileChooserIconView(
            path=default_path or ".",
            filters=self.file_types
        )
        self.filechooser.bind(selection=self.update_filename_input)
        self.filechooser.bind(path=self.update_path_label)
        central_layout.add_widget(self.filechooser)

        # Input + Spinner en horizontal
        input_layout = BoxLayout(orientation="horizontal", size_hint_y=None, height=30, spacing=5)

        self.filename_input = TextInput(
            text="", multiline=False, hint_text="Nombre de archivo"
        )
        input_layout.add_widget(self.filename_input)

        self.filter_spinner = Spinner(
            text=self.file_types[0], 
            values=self.file_types, 
            size_hint_x=None, 
            width=100
        )
        self.filter_spinner.bind(text=self.set_filter)
        input_layout.add_widget(self.filter_spinner)

        central_layout.add_widget(input_layout)
        if self.mode in ["open"]:
            self.filename_input.readonly = True  # no editable
            self.filename_input.text = ""

        # Botones inferiores
        btn_layout = BoxLayout(size_hint_y=None, height=40, spacing=5)

        btn_new_folder = Button(text="Nueva carpeta")
        btn_new_folder.bind(on_release=self.create_folder)
        btn_layout.add_widget(btn_new_folder)

        btn_ok = Button(text="Aceptar")
        btn_ok.bind(on_release=self.on_ok)
        btn_layout.add_widget(btn_ok)

        btn_cancel = Button(text="Cancelar")
        btn_cancel.bind(on_release=self.dismiss)
        btn_layout.add_widget(btn_cancel)

        central_layout.add_widget(btn_layout)
        main_layout.add_widget(central_layout)

        self.content = main_layout

    def update_path_label(self, instance, value):
        """Actualizar el label de la ruta cuando cambie el directorio."""
        self.path_label.text = value

    def change_dir(self, path):
        if os.path.exists(path):
            self.filechooser.path = path

    def set_filter(self, spinner, text):
        self.filechooser.filters = [text]

    def create_folder(self, instance):
        new_folder = os.path.join(self.filechooser.path, "Nueva Carpeta")
        i = 1
        while os.path.exists(new_folder):
            new_folder = os.path.join(self.filechooser.path, f"Nueva Carpeta {i}")
            i += 1
        os.mkdir(new_folder)
        self.filechooser._update_files()

    def update_filename_input(self, instance, selection):
        if self.filename_input and selection:
            self.filename_input.text = os.path.basename(selection[0])

    def on_ok(self, instance):
        path = self.filechooser.path
        if self.mode in ["save", "new"]:
            filename = self.filename_input.text.strip()
            if not filename:
                return
            full_path = os.path.join(path, filename)
        else:
            if not self.filechooser.selection:
                return
            full_path = self.filechooser.selection[0]

        save_recent_path(path)

        if self.callback:
            self.callback(full_path)
        self.dismiss()

