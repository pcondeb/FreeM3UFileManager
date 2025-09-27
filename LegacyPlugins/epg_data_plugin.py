# plugins/epg_data_plugin_full.py
import os, gzip, io, requests, xml.etree.ElementTree as ET
from threading import Thread
from kivy.uix.popup import Popup
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label
from kivy.uix.image import AsyncImage
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock
from kivy.graphics import Color, Line

# --- utils ---
def popup_message(title, text):
    layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
    label = Label(text=text)
    btn = Button(text='OK', size_hint_y=None, height=40)
    layout.add_widget(label)
    layout.add_widget(btn)
    popup = Popup(title=title, content=layout, size_hint=(None, None), size=(400, 200))
    btn.bind(on_release=popup.dismiss)
    popup.open()

# --- botón canal ---
class ChannelButtonWithFallback(ButtonBehavior, FloatLayout):
    def __init__(self, epg_channel, fallback_text="", **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.width = 150
        self.height = 150
        self.epg_channel = epg_channel
        self.fallback_text = fallback_text
        self._selected = False

        # Layout interno vertical centrado
        self.inner_layout = BoxLayout(orientation='vertical', spacing=5, padding=5, size_hint=(1,1), pos_hint={"center_x":0.5,"center_y":0.5})
        self.add_widget(self.inner_layout)

        # Imagen
        self.img = AsyncImage(allow_stretch=True, keep_ratio=True)
        self.inner_layout.add_widget(self.img)

        # Texto
        self._label_widget = Label(
            text=self.fallback_text,
            color=(1, 1, 1, 1),
            halign="center",
            valign="middle",
            size_hint=(1, None),
            height=30,
        )
        self._label_widget.bind(size=self._update_text)
        self.inner_layout.add_widget(self._label_widget)

        # borde de selección
        with self.canvas.after:
            self._border_color = Color(0, 0, 0, 0)
            self._border_line = Line(rectangle=(self.x, self.y, self.width, self.height), width=3)
        self.bind(pos=self._update_border, size=self._update_border)

    def _update_border(self, *args):
        self._border_line.rectangle = (self.x, self.y, self.width, self.height)

    def _update_text(self, *args):
        self._label_widget.text_size = (self._label_widget.width, self._label_widget.height)

    def set_selected(self, value: bool):
        self._selected = value
        self._border_color.rgba = (0.27, 0.55, 0.93, 1) if value else (0, 0, 0, 0)

    def texture_update_from_data(self, data):
        try:
            buf = io.BytesIO(data)
            im = CoreImage(buf, ext="png")
            self.img.texture = im.texture
        except Exception:
            self._label_widget.text = self.fallback_text

    def set_fallback_text(self):
        self._label_widget.text = self.fallback_text


# --- plugin principal ---
class EpgDataPlugin:
    name = "Legacy Plugins/EPG Data Plugin"

    def __init__(self, config_manager=None, check_init=False):
        self.config = config_manager
        self.epg_channels = []
        self.epg_source = ""
        self.load_on_start = False
        self._cached_buttons = {}
        self._preloading = False

        plugin_cfg_key = f"plugin_{self.name.replace('/','_')}"
        if self.config:
            if plugin_cfg_key not in self.config.config:
                self.config.config[plugin_cfg_key] = {}
                self.config.save()
            self.epg_source = self.config.get("source", "", section=plugin_cfg_key)
            self.load_on_start = self.config.get_bool("load_on_start", False, section=plugin_cfg_key)

        if check_init:
            return

        if self.load_on_start and self.epg_source:
            if self.load_epg_from_source():
                self.preload_buttons()
        else:
            if not self.epg_source:
                self.configure(None)

    # --- configuración ---
    def _open_plugin_config_menu_(self, parent=None):
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        url_label = Label(text="EPG URL or local path:", size_hint_y=None, height=30)
        self.url_input = TextInput(text=self.epg_source, multiline=False)
        layout.add_widget(url_label)
        layout.add_widget(self.url_input)

        load_layout = BoxLayout(orientation="horizontal", size_hint_y=None, height=40)
        self.load_cb = CheckBox(active=self.load_on_start)
        load_layout.add_widget(Label(text="Load on start"))
        load_layout.add_widget(self.load_cb)
        layout.add_widget(load_layout)

        btn_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        btn_save = Button(text="Save")
        btn_cancel = Button(text="Cancel")
        btn_layout.add_widget(btn_save)
        btn_layout.add_widget(btn_cancel)
        layout.add_widget(btn_layout)

        popup = Popup(title=f"{self.name} - Configuration", content=layout, size_hint=(0.6,0.6))
        btn_save.bind(on_release=lambda *a: self._save_config(popup))
        btn_cancel.bind(on_release=lambda *a: popup.dismiss())
        popup.open()
		
    def _save_config(self, popup):
        self.epg_source = self.url_input.text.strip()
        self.load_on_start = self.load_cb.active
        if self.config:
            plugin_cfg_key = f"plugin_{self.name.replace('/','_')}"
            if plugin_cfg_key not in self.config.config:
                self.config.config[plugin_cfg_key] = {}
            self.config.set("source", self.epg_source, section=plugin_cfg_key)
            self.config.set("load_on_start", str(self.load_on_start), section=plugin_cfg_key)
        popup.dismiss()

    def get_functions(self):
        return [
            ("Assign All", self.assign_all),
            ("Assign.../tvg-logo", self.assign_tvg_logo),
            ("Assign.../tvg-id", self.assign_tvg_id),
            ("Assign.../tvg-name", self.assign_tvg_name),
            ("Assign.../tvg-url", self.assign_tvg_url),
            ("Configure EPG Source", self.configure),
        ]
		
    def configure(self, editor_window):
        content = BoxLayout(orientation="vertical", padding=10, spacing=10)
        txt = TextInput(text=self.epg_source, multiline=False, hint_text="Enter EPG URL or local path")
        content.add_widget(txt)
        btn_ok = Button(text="OK", size_hint_y=None, height=40)
        content.add_widget(btn_ok)
        popup = Popup(title="EPG Plugin", content=content, size_hint=(0.7, 0.3))
        btn_ok.bind(on_release=lambda *a: self._do_config(txt.text, popup))
        popup.open()

    def _do_config(self, url, popup):
        popup.dismiss()
        if not url.strip():
            return
        self.epg_source = url.strip()
        success = self.load_epg_from_source()
        if success:
            self.preload_buttons()

    # --- carga EPG ---
    def load_epg_from_source(self):
        if not self.epg_source:
            return False
        try:
            if self.epg_source.startswith("http"):
                response = requests.get(self.epg_source, timeout=10)
                content = response.content
                if self.epg_source.endswith(".gz"):
                    with gzip.GzipFile(fileobj=io.BytesIO(content)) as f:
                        tree = ET.parse(f)
                else:
                    tree = ET.ElementTree(ET.fromstring(content))
            else:
                if self.epg_source.endswith(".gz"):
                    with gzip.open(self.epg_source, "rb") as f:
                        tree = ET.parse(f)
                else:
                    tree = ET.parse(self.epg_source)

            root = tree.getroot()
            self.epg_channels = []
            for ch in root.findall("channel"):
                ch_data = {
                    "tvg-id": ch.attrib.get("id", ""),
                    "tvg-name": "",
                    "tvg-logo": "",
                    "tvg-url": "",
                    "name": ch.attrib.get("id", ""),
                    "icon_url": None,
                }
                dn = ch.find("display-name")
                if dn is not None:
                    ch_data["tvg-name"] = dn.text or ""
                icon = ch.find("icon")
                if icon is not None:
                    ch_data["tvg-logo"] = icon.attrib.get("src", "")
                    if ch_data["tvg-logo"]:
                        ch_data["icon_url"] = ch_data["tvg-logo"]
                url = ch.find("url")
                if url is not None:
                    ch_data["tvg-url"] = url.text or ""
                self.epg_channels.append(ch_data)
            return True
        except Exception as e:
            print(f"[EPGDataPlugin] Failed to load EPG: {e}")
            self.epg_channels = []
            return False

    # --- preload botones ---
    def preload_buttons(self):
        if self._preloading or not self.epg_channels:
            return
        self._preloading = True
        self._cached_buttons.clear()
        self._preload_index = 0
        self._total = len(self.epg_channels)
        self._popup_label = Label(text=f"Preparing 0/{self._total}")
        self._popup = Popup(
            title="Loading channels...",
            content=self._popup_label,
            size_hint=(None, None),
            size=(320, 120),
            auto_dismiss=False,
        )
        self._popup.open()

        def load_next_channel(dt=None):
            if self._preload_index >= self._total:
                self._preloading = False
                self._popup.dismiss()
                return False
            ch = self.epg_channels[self._preload_index]
            btn = ChannelButtonWithFallback(epg_channel=ch, fallback_text=ch.get("tvg-name", ""))
            btn.size_hint = (None, None)   # no queremos que el GridLayout lo escale automáticamente
            btn.width = 150
            btn.height = 150
            self._cached_buttons[ch["name"]] = (btn, ch)

            def download_image():
                url = ch.get("icon_url")
                try:
                    if url:
                        r = requests.get(url, timeout=5)
                        if r.status_code == 200:
                            data = r.content
                            Clock.schedule_once(lambda dt: btn.texture_update_from_data(data))
                        else:
                            Clock.schedule_once(lambda dt: btn.set_fallback_text())
                    else:
                        Clock.schedule_once(lambda dt: btn.set_fallback_text())
                except:
                    Clock.schedule_once(lambda dt: btn.set_fallback_text())
                finally:
                    self._preload_index += 1
                    self._popup_label.text = f"Preparing {self._preload_index}/{self._total}"

            Thread(target=download_image, daemon=True).start()
            return True

        Clock.schedule_interval(load_next_channel, 0.1)

    # --- ventana mosaico ---
    class EpgMosaicWindow(Popup):
        def __init__(self, epg_channels, plugin_instance, on_select=None, **kwargs):
            super().__init__(**kwargs)
            self.title = "Select EPG Channel"
            self.size_hint = (0.9, 0.9)
            self.auto_dismiss = False
            self.epg_channels = epg_channels
            self.plugin_instance = plugin_instance
            self.on_select = on_select
            self.selected_channel = None
            self.selected_btn = None

            main_layout = BoxLayout(orientation='vertical', spacing=5, padding=5)
            self.filter_input = TextInput(
                hint_text="Filter by name...", size_hint_y=None, height=30, multiline=False
            )
            self.filter_input.bind(text=self.apply_filter)
            main_layout.add_widget(self.filter_input)

            scroll = ScrollView()
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
            self.grid.bind(minimum_height=self.grid.setter("height"))
            scroll.add_widget(self.grid)
            main_layout.add_widget(scroll)

            self.info_label = Label(size_hint_y=None, height=40, text="Select a channel", valign="top")
            main_layout.add_widget(self.info_label)

            btn_layout = BoxLayout(size_hint_y=None, height=40, spacing=5)
            btn_ok = Button(text="OK")
            btn_cancel = Button(text="Cancel")
            btn_ok.bind(on_release=self._accept)
            btn_cancel.bind(on_release=self.dismiss)
            btn_layout.add_widget(btn_ok)
            btn_layout.add_widget(btn_cancel)
            main_layout.add_widget(btn_layout)
            self.add_widget(main_layout)

            # cache
            self._buttons = []
            for ch in self.epg_channels:
                cached = self.plugin_instance._cached_buttons.get(ch.get("name"))
                if cached:
                    btn = cached[0]
                else:
                    btn = ChannelButtonWithFallback(epg_channel=ch, fallback_text=ch.get("tvg-name", ""))
                self._buttons.append((btn, ch))
            self.apply_filter()

            self.bind(width=self.update_cols)
            self.update_cols()  # inicial

        def update_cols(self, *args):
            col_width = self.grid.col_default_width + self.grid.spacing[0]  # ancho de columna + spacing
            available_width = self.width - self.grid.padding[0]*2
            self.grid.cols = max(1, int(available_width // col_width))

        def apply_filter(self, *args):
            query = self.filter_input.text.strip().lower()
            self.grid.clear_widgets()
            for btn, ch in self._buttons:
                if query and query not in ch.get("tvg-name", "").lower():
                    continue
                if btn.parent:
                    btn.parent.remove_widget(btn)
                btn.set_selected(btn is self.selected_btn)
                btn.bind(on_release=lambda inst, b=btn, c=ch: self.select_channel(c, b))
                self.grid.add_widget(btn)

        def select_channel(self, ch, btn):
            if self.selected_btn:
                self.selected_btn.set_selected(False)
            self.selected_btn = btn
            btn.set_selected(True)
            self.selected_channel = ch
            self.info_label.text = f"Selected: {ch.get('tvg-name','')}"

        def _accept(self, *args):
            if self.on_select and self.selected_channel:
                self.on_select(self.selected_channel)
            self.dismiss()

    # --- assign ---
    def assign_field(self, editor_window, field_names):
        if not self.epg_channels:
            popup_message("EPG Plugin", "❌ No EPG loaded.")
            return

        if isinstance(field_names, str):
            field_names = [field_names]

        def find_real_node(data_ref, key_path):
            ref = data_ref
            for k in key_path:
                if isinstance(ref, dict):
                    ref = ref.get(k)
                else:
                    return None
            return ref

        def apply_to_node(node_ref, ch, field):
            if not node_ref:
                return False
            if isinstance(node_ref, dict):
                node_ref[field] = self.epg_source if field == "tvg-url" else ch.get(field, "")
                return True
            elif isinstance(node_ref, list):
                updated = False
                for c in node_ref:
                    if isinstance(c, dict):
                        c[field] = self.epg_source if field == "tvg-url" else ch.get(field, "")
                        updated = True
                return updated
            return False

        def on_select(ch):
            if not ch:
                return
            selected_items = [item for item in editor_window.editor_helper.items if item.selected]
            if not selected_items:
                popup_message("Sin selección", "Selecciona canales o grupos en el editor.")
                return

            updated = False
            for item in selected_items:
                node = getattr(item, "data", None)
                if not node:
                    continue

                # caso: canal identificado por unique_id
                if isinstance(node, str):
                    parent_node = find_real_node(editor_window.data, editor_window.editor_helper.current_path)
                    if parent_node and "_channels" in parent_node:
                        for c in parent_node["_channels"]:
                            if c.get("_unique_id") == node:
                                for field in field_names:
                                    if apply_to_node(c, ch, field):
                                        updated = True

                # caso: grupo con "key"
                elif isinstance(node, dict) and "key" in node:
                    key_path = editor_window.editor_helper.current_path + [node["key"]]
                    real_node = find_real_node(editor_window.data, key_path)
                    if real_node:
                        for field in field_names:
                            if apply_to_node(real_node.get("_channels", []), ch, field):
                                updated = True

                # caso: canal dict
                elif isinstance(node, dict):
                    parent_node = find_real_node(editor_window.data, editor_window.editor_helper.current_path)
                    if parent_node and "_channels" in parent_node:
                        for c in parent_node["_channels"]:
                            if c is node or c.get("name") == node.get("name"):
                                for field in field_names:
                                    if apply_to_node(c, ch, field):
                                        updated = True

            if updated:
                try:
                    editor_window.editor_helper.populate_list()
                except Exception:
                    pass
                popup_message("Éxito", f"Se aplicaron los campos: {', '.join(field_names)} correctamente.")
            else:
                popup_message("Sin cambios", "No se aplicaron cambios.")

        win = self.EpgMosaicWindow(self.epg_channels, self, on_select=on_select)
        win.open()

    def assign_tvg_logo(self, editor_window):
        self.assign_field(editor_window, "tvg-logo")

    def assign_tvg_id(self, editor_window):
        self.assign_field(editor_window, "tvg-id")

    def assign_tvg_name(self, editor_window):
        self.assign_field(editor_window, "tvg-name")

    def assign_tvg_url(self, editor_window):
        self.assign_field(editor_window, "tvg-url")

    def assign_all(self, editor_window):
        self.assign_field(editor_window, ["tvg-logo", "tvg-id", "tvg-name", "tvg-url"])


plugin_class = EpgDataPlugin
