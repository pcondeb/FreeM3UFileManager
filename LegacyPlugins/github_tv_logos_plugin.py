# -*- coding: utf-8 -*-

import os
import shutil
import zipfile
import requests
from copy import deepcopy
from pathlib import Path

from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.core.window import Window
from kivy.uix.image import AsyncImage
from kivy.clock import Clock
from kivy.graphics import Color, Line
from app.paths_module import get_user_data_dir

try:
    from app.diff_dialog import DiffDialog
except Exception:
    DiffDialog = None

LOGO_REPO_URL = "https://github.com/tv-logo/tv-logos/archive/refs/heads/master.zip"
GITHUB_BASE_URL = "https://raw.githubusercontent.com/tv-logo/tv-logos/master/"
DEFAULT_REPO_PATH = get_user_data_dir() / "logos_repo"
CONFIG_SECTION = "Legacy Plugins/GitHub TV Logos Plugin"


def popup_message(title, text):
    layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
    label = Label(text=text)
    btn = Button(text='OK', size_hint_y=None, height=40)
    layout.add_widget(label)
    layout.add_widget(btn)
    popup = Popup(title=title, content=layout, size_hint=(None, None), size=(400, 200))
    btn.bind(on_release=popup.dismiss)
    popup.open()


class LogoButton(ButtonBehavior, AsyncImage):
    def __init__(self, source, url=None, load_callback=None, **kwargs):
        super().__init__(source=source, **kwargs)
        self.url = url  # <-- guardamos la URL real de GitHub
        self._load_callback = load_callback
        self._loaded = False
        self._selected = False

        self.bind(texture=self._on_texture)
        with self.canvas.after:
            self._border_color = Color(0, 0, 0, 0)
            self._border_line = Line(rectangle=(self.x, self.y, self.width, self.height), width=2)
        self.bind(pos=self._update_border, size=self._update_border)

    def _on_texture(self, instance, tex):
        if tex and not self._loaded:
            self._loaded = True
            if self._load_callback:
                Clock.schedule_once(lambda dt: self._load_callback(self), 0)

    def set_selected(self, value: bool):
        self._selected = bool(value)
        self._border_color.rgba = (0.27, 0.55, 0.93, 1) if self._selected else (0, 0, 0, 0)

            
    def _update_border(self, *args):
        try:
            self._border_line.rectangle = (self.x, self.y, self.width, self.height)
        except Exception:
            pass


class GithubTVLogosPlugin:
    name = "Legacy Plugins/GitHub TV Logos Plugin"

    def __init__(self, config_manager=None, plugin_manager=None, check_init=False):
        self.config_manager = config_manager
        self.plugin_manager = plugin_manager

        self.repo_path = DEFAULT_REPO_PATH
        self.logo_entries = []
        self.logos_loaded = False
        self.menu_generated = False
        self.path_input = None
        self.default_country = None

        # caché de botones por país: { country: [(btn, entry), ...] }
        self._cached_buttons = {}

        self._preloading = {}  # control de preloads en curso por país

        self._load_config()

        if check_init:
            return

        # Si hay repo y país asignado, precargar entradas (no botones)
        if os.path.exists(self.repo_path) and any(os.scandir(self.repo_path)) and self.default_country:
            try:
                self.generate_entries(country_filter=self.default_country)
                self.logos_loaded = len(self.logo_entries) > 0
            except Exception:
                self.logos_loaded = False
                self.logo_entries = []

    # ---------------------- Config ----------------------
    def _load_config(self):
        if not self.config_manager:
            return
        plugin_cfg_key = f"plugin_{self.name.replace('/', '_')}"
        self.repo_path = self.config_manager.get("repo_path", DEFAULT_REPO_PATH, section=plugin_cfg_key)
        self.default_country = self.config_manager.get("default_country", None, section=plugin_cfg_key)

    def _save_plugin_config(self):
        if not self.config_manager:
            return
        plugin_cfg_key = f"plugin_{self.name.replace('/', '_')}"
        if not self.repo_path:
            self.repo_path = DEFAULT_REPO_PATH
        self.config_manager.set("repo_path", self.repo_path, section=plugin_cfg_key)
        if self.default_country:
            self.config_manager.set("default_country", self.default_country, section=plugin_cfg_key)
        else:
            try:
                if "default_country" in self.config_manager.config.get(plugin_cfg_key, {}):
                    del self.config_manager.config[plugin_cfg_key]["default_country"]
            except Exception:
                pass
        try:
            self.config_manager.save()
        except Exception:
            pass
        popup_message("Settings", "Repo path saved successfully.")

    # ---------------------- Funciones para menú de plugin ----------------------
    def get_functions(self):
        return [
            ("Assign logo", self.assign_tvg_logo),
            ("Update local Repo", self.update_repo),
            ("Configure Repo Path", self._open_plugin_config_menu_),
        ]

    # ---------------------- Obtener lista de países ----------------------
    def _get_repo_countries(self):
        countries = []
        countries_path = os.path.join(self.repo_path, 'countries')
        if os.path.exists(countries_path):
            for entry in os.listdir(countries_path):
                full = os.path.join(countries_path, entry)
                if os.path.isdir(full):
                    countries.append(entry)
        return sorted(countries)

    # ---------------------- Selector país (Kivy) ----------------------
    def _ask_country(self):
        countries = self._get_repo_countries()
        if not countries:
            popup_message("Logos Repo", "❌ No countries found in repo.")
            return None
        if len(countries) == 1:
            return countries[0]

        self._country_selected = None
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        spinner = Spinner(text=countries[0], values=countries)
        layout.add_widget(spinner)
        btn = Button(text='OK', size_hint_y=None, height=40)
        layout.add_widget(btn)
        popup = Popup(title="Select country to load logos", content=layout, size_hint=(None, None), size=(400, 200))
        btn.bind(on_release=lambda x: self._set_country(spinner.text, popup))
        popup.open()
        return None  # queda guardado en self.default_country por _set_country

    def _set_country(self, country, popup):
        self.default_country = country
        try:
            self._save_plugin_config()
        except Exception:
            pass
        self._country_selected = country
        popup.dismiss()

    def _ensure_country_selected(self):
        # Si no hay repo, descargarlo primero
        if not os.path.exists(self.repo_path) or not any(os.scandir(self.repo_path)):
            try:
                # forzamos descarga sin preguntar por país (se preguntará después)
                self.update_repo()
            except Exception as e:
                popup_message("Logos Repo", f"❌ Failed to download repo: {e}")
                return False

        # Ahora sí preguntar por país si no hay default_country
        if not self.default_country:
            country = self._ask_country()
            if not country:
                return False
            self.default_country = country
        return True

    # ---------------------- Repo updater ----------------------
    def update_repo(self, editor_window=None):
        try:
            if os.path.exists(self.repo_path):
                shutil.rmtree(self.repo_path)
            os.makedirs(self.repo_path, exist_ok=True)

            zip_path = get_user_data_dir() / "tv-logos.zip"
            resp = requests.get(LOGO_REPO_URL, stream=True, timeout=60)
            resp.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            # Extraer a carpeta temporal
            temp_dir = "tv_logos_temp"
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)
            os.remove(zip_path)

            # Mover todo el contenido de la carpeta extraída a repo_path
            extracted_folder = next((d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))), None)
            if not extracted_folder:
                raise FileNotFoundError('No se encontró la carpeta extraída del repo')

            src_path = os.path.join(temp_dir, extracted_folder)
            for item in os.listdir(src_path):
                shutil.move(os.path.join(src_path, item), self.repo_path)

            shutil.rmtree(temp_dir)

            self.generate_entries(country_filter=self.default_country)
            self.logos_loaded = len(self.logo_entries) > 0
            self.menu_generated = False
            popup_message("Logos Repo", "✅ Logos repo updated successfully.")
        except Exception as e:
            popup_message("Logos Repo", f"❌ Failed to update repo: {e}")

    # ---------------------- Generar entradas ----------------------
    def generate_entries(self, country_filter=None):
        self.logo_entries.clear()
        if not os.path.exists(self.repo_path):
            return
        for root, _, files in os.walk(self.repo_path):
            for f in files:
                if not f.lower().endswith((".png", ".jpg", ".jpeg", ".svg")):
                    continue
                local_path = os.path.join(root, f)
                rel_path = os.path.relpath(local_path, self.repo_path).replace("\\", "/")
                parts = rel_path.split('/')
                country = 'unknown'
                if parts and parts[0].lower() == 'countries' and len(parts) > 1:
                    country = parts[1]
                elif parts:
                    country = parts[0]
                if country_filter and country != country_filter:
                    continue
                url = GITHUB_BASE_URL + rel_path
                self.logo_entries.append({
                    'country': country,
                    'local_path': local_path,
                    'url': url,
                    'filename': f,
                })
        self.logo_entries.sort(key=lambda e: (e['country'].lower() if e['country'] else '', e['filename'].lower()))

    # ---------------------- Config dialog (Kivy) ----------------------
    def _open_plugin_config_menu_(self, parent=None):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.path_input_widget = TextInput(text=str(self.repo_path), multiline=False)
        layout.add_widget(Label(text="Local Repo Path:"))
        layout.add_widget(self.path_input_widget)

        countries = self._get_repo_countries()
        self.country_spinner = Spinner(text=self.default_country or "", values=countries)
        layout.add_widget(Label(text="Default Country:"))
        layout.add_widget(self.country_spinner)

        btn_layout = BoxLayout(size_hint_y=None, height=50)
        btn_save = Button(text="Save")
        btn_update = Button(text="Update Repo")
        btn_cancel = Button(text="Cancel")
        btn_layout.add_widget(btn_save)
        btn_layout.add_widget(btn_update)
        btn_layout.add_widget(btn_cancel)
        layout.add_widget(btn_layout)

        popup = Popup(title="GitHub TV Logos Config", content=layout, size_hint=(None, None), size=(700, 500))

        btn_save.bind(on_release=lambda x: self._save_plugin_config_from_widget(popup))
        btn_update.bind(on_release=lambda x: (self.update_repo(), popup.dismiss()))
        btn_cancel.bind(on_release=popup.dismiss)
        popup.open()

    def _save_plugin_config_from_widget(self, popup):
        self.repo_path = self.path_input_widget.text.strip() or DEFAULT_REPO_PATH
        self.default_country = self.country_spinner.text or None
        self._save_plugin_config()
        popup.dismiss()

    # ---------------------- Mosaic Window ----------------------
    class LogoMosaicWindow(Popup):
        def __init__(self, entries, plugin_instance, on_select=None, cached_buttons=None, **kwargs):
            super().__init__(**kwargs)
            self.title = "Select TV Logo"
            self.size_hint = (None, None)
            self.size_hint = (0.9, 0.9)
            self.entries = entries
            self.plugin_instance = plugin_instance
            self.selected_url = None
            self.on_select = on_select
            self.selected_btn = None

            layout = BoxLayout(orientation='vertical', spacing=5, padding=5)
            self.filter_input = TextInput(hint_text="Filter by name...", size_hint_y=None, height=30, multiline=False)
            self.filter_input.bind(text=self.apply_filter)
            layout.add_widget(self.filter_input)

            self.scroll = ScrollView(size_hint=(1, 1))
            self.grid = GridLayout(
                cols=10,
                spacing=10,
                padding=10,
                size_hint_y=None,
                row_default_height=150,
                col_default_width=150,
                row_force_default=True,
                col_force_default=True,
            )
            self.grid.bind(minimum_height=self.grid.setter('height'))
            self.scroll.add_widget(self.grid)
            layout.add_widget(self.scroll)

            btn_layout = BoxLayout(size_hint_y=None, height=40, spacing=5)
            self.btn_ok = Button(text="OK")
            btn_cancel = Button(text="Cancel")
            btn_layout.add_widget(self.btn_ok)
            btn_layout.add_widget(btn_cancel)
            layout.add_widget(btn_layout)

            self.btn_ok.bind(on_release=self._on_ok)
            btn_cancel.bind(on_release=self.dismiss)

            self.content = layout

            # si vienen botones ya precargados los usamos
            # cached_buttons: list of (btn, entry)
            self._image_buttons = cached_buttons if cached_buttons is not None else []
            # si la lista se pasará vacía, apply_filter la poblará correctamente
            self.apply_filter()
            
            # recalcular columnas cuando cambia el tamaño del popup
            self.bind(width=self.update_cols)
            self.update_cols()  # inicial

        def update_cols(self, *args):
            col_width = self.grid.col_default_width + self.grid.spacing[0]  # ancho de columna + spacing
            available_width = self.width - self.grid.padding[0]*2
            self.grid.cols = max(1, int(available_width // col_width))

        def apply_filter(self, *args):
            query = self.filter_input.text.strip().lower()
            self.grid.clear_widgets()
            for btn, entry in self._image_buttons:
                if query and query not in entry['filename'].lower():
                    continue
                # rebind on_release a la función select; cuando se mueven entre padres los bindings se mantienen,
                # pero aseguramos pasar el botón en la lambda para evitar late-binding.
                # además restauramos el estado de selección visual
                btn.set_selected(btn is self.selected_btn)
                # atamos evento on_release para seleccionar este botón
                btn.unbind(on_release=None)  # intento por eliminar bindings previos, no garantiza todo
                btn.bind(on_release=lambda inst, b=btn: self.select(b))
                if btn.parent:
                    btn.parent.remove_widget(btn)
                self.grid.add_widget(btn)

        def select(self, btn):
            if self.selected_btn:
                self.selected_btn.set_selected(False)
            self.selected_btn = btn
            btn.set_selected(True)
            # source puede ser local path o URL: usamos la propiedad 'source' de AsyncImage
            self.selected_url = btn.url

        def _on_ok(self, *args):
            self.dismiss()
            if self.on_select:
                self.on_select(self.selected_url)

        def get_selected_logo(self):
            return self.selected_url

    # ---------------------- Assign ----------------------
    def assign_field(self, editor_window, field_name):
        # Aseguramos país / repo / entries
        if not self._ensure_country_selected():
            return
        if not self.logos_loaded:
            self.generate_entries(country_filter=self.default_country)
            self.logos_loaded = len(self.logo_entries) > 0
        if not self.logo_entries:
            popup_message("Logos Repo", "❌ No logos found.")
            return

        # Filtramos por país seleccionado
        country = self.default_country
        entries_for_country = [e for e in self.logo_entries if e.get('country') == country]

        if not entries_for_country:
            popup_message("Logos Repo", f"❌ No logos found for country: {country}")
            return

        # Si ya tenemos caché completa para este país, abrir mosaico directamente
        cached = self._cached_buttons.get(country)
        if cached and len(cached) >= len(entries_for_country):
            dlg = self.LogoMosaicWindow(entries_for_country, self, on_select=lambda url: self._on_logo_chosen(editor_window, field_name, url), cached_buttons=cached)
            dlg.open()
            return

        # Si hay un preload en curso para este país, mostramos un popup corto y esperamos su finalización
        if self._preloading.get(country):
            popup_message("Logos Repo", "Preloading already in progress, please wait a moment...")
            return

        # Popup de carga (preparando botones)
        loading_popup = Popup(
            title="Cargando logos...",
            content=Label(text=f"Preparando 0 / {len(entries_for_country)}"),
            size_hint=(None, None), size=(320, 120),
            auto_dismiss=False
        )
        loading_popup.open()

        # Preparamos botones y los vamos llenando
        image_buttons = []
        total = len(entries_for_country)
        counter = {'n': 0}
        country_key = country
        self._preloading[country_key] = True

        def _on_btn_loaded(btn):
            # se llama desde el hilo principal (Clock.schedule)
            counter['n'] += 1
            loading_popup.content.text = f"Cargando {counter['n']} / {total}"
            if counter['n'] >= total:
                # guardamos en caché y abrimos mosaico
                self._cached_buttons[country_key] = image_buttons.copy()
                self._preloading.pop(country_key, None)
                loading_popup.dismiss()
                dlg = self.LogoMosaicWindow(entries_for_country, self, on_select=lambda url: self._on_logo_chosen(editor_window, field_name, url), cached_buttons=self._cached_buttons[country_key])
                dlg.open()

        # crear botones (usa local_path si existe, evitando HTTP cuando sea posible)
        for entry in entries_for_country:
            src = entry.get('local_path') if entry.get('local_path') and os.path.exists(entry.get('local_path')) else entry.get('url')
            btn = LogoButton(source=src, url=entry.get('url'), load_callback=lambda inst, cb=_on_btn_loaded: cb(inst),
                             size=(150,150), size_hint=(None,None))
            if getattr(btn, '_loaded', False):
                # si ya cargada, añadimos y notificamos
                image_buttons.append((btn, entry))
                Clock.schedule_once(lambda dt, _btn=btn: _on_btn_loaded(_btn), 0)
            else:
                # añadimos y esperamos al callback cuando texture esté disponible
                image_buttons.append((btn, entry))
                # Nota: LogoButton llamará al load_callback cuando la textura esté lista
                # No hacemos nada extra aquí
                pass

        # Si no había entradas (paranoia), cerramos y avisamos
        if total == 0:
            loading_popup.dismiss()
            popup_message("Logos Repo", "❌ No logos to load.")
            self._preloading.pop(country_key, None)
            return

    def _on_logo_chosen(self, editor_window, field_name, selected_logo):
        """
        Callback que se llama cuando el usuario elige un logo en el mosaico.
        Aquí aplicamos el campo a los nodos seleccionados.
        """
        if not selected_logo:
            popup_message("No selection", "Please select a logo first.")
            return

        selected_items = [i for i in editor_window.editor_helper.items if getattr(i, 'selected', False)]
        if not selected_items:
            popup_message("No selection", "Please select channels or groups in the editor.")
            return

        updated = False

        def apply_to_node(node_ref):
            nonlocal updated
            if isinstance(node_ref, dict):
                node_ref[field_name] = selected_logo
                updated = True
            elif isinstance(node_ref, list):
                for ch in node_ref:
                    if isinstance(ch, dict):
                        ch[field_name] = selected_logo
                        updated = True

        def find_real_node(data_ref, key_path):
            ref = data_ref
            for k in key_path:
                if isinstance(ref, dict):
                    ref = ref.get(k)
                else:
                    return None
            return ref

        for item in selected_items:
            node = getattr(item, 'node', None)
            if not node:
                continue

            # unique id string
            if isinstance(node, str):
                parent_node = find_real_node(editor_window.data, editor_window.editor_helper.current_path)
                if parent_node and "_channels" in parent_node:
                    for ch in parent_node["_channels"]:
                        if ch.get("_unique_id") == node:
                            apply_to_node(ch)

            # group node with key => apply to that group's _channels
            elif isinstance(node, dict) and "key" in node:
                key_path = editor_window.editor_helper.current_path + [node["key"]]
                real_node = find_real_node(editor_window.data, key_path)
                if real_node:
                    apply_to_node(real_node.get("_channels", []))

            # a channel dict or list entry => find by identity or name
            elif isinstance(node, dict):
                parent_node = find_real_node(editor_window.data, editor_window.editor_helper.current_path)
                if parent_node and "_channels" in parent_node:
                    for ch in parent_node["_channels"]:
                        if ch is node or ch.get("name") == node.get("name"):
                            apply_to_node(ch)

        if updated:
            try:
                editor_window.editor_helper.populate_list()
            except Exception:
                pass
            popup_message("Éxito", f"Se aplicó el campo {field_name} correctamente.")
        else:
            popup_message("Sin cambios", "No se aplicaron cambios.")

    def assign_tvg_logo(self, editor_window):
        self.assign_field(editor_window, "tvg-logo")


plugin_class = GithubTVLogosPlugin
