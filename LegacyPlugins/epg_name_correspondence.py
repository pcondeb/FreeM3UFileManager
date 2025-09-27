# -*- coding: utf-8 -*-
"""
Plugin: EpgNameCorrespondence
Archivo: epg_name_correspondence.py
Guarda/carga/edita correspondencias de canales (key=name).
"""

import os
import json
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from app.add_channel_dialog import AddChannelDialog
from app.paths_module import get_user_data_dir

# ======================= Utils =======================

def popup_message(title, text):
    layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
    label = Label(text=text)
    btn = Button(text='OK', size_hint_y=None, height=40)
    layout.add_widget(label)
    layout.add_widget(btn)
    popup = Popup(title=title, content=layout, size_hint=(None, None), size=(400, 200))
    btn.bind(on_release=popup.dismiss)
    popup.open()


# ======================= Plugin =======================

class EpgNameCorrespondence:
    """Plugin para guardar/cargar correspondencias de canales por nombre."""

    name = "Legacy Plugins/Epg-Name Correspondence"

    def __init__(self, config_manager=None, plugin_manager=None, check_init=False):
        self.config_manager = config_manager
        self.plugin_manager = plugin_manager
        self.data_file = get_user_data_dir() / "epg_name_data.json"
        self.data = {}

        if check_init:
            return

        self._load_data()

    # ---------------------- Funciones de menú ----------------------
    def get_functions(self):
        return [
            ("Save selected channels data", self.save_selected_channels),
            ("Load selected channels data", self.load_selected_channels),
            ("Edit correspondence", self.edit_correspondences),
            ("Configure plugin", self._open_plugin_config_menu_),
        ]

    # ---------------------- Persistencia ----------------------
    def _load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                popup_message("Error", f"No se pudo cargar {self.data_file}\n{e}")
                self.data = {}

    def _save_data(self):
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            popup_message("Error", f"No se pudo guardar {self.data_file}\n{e}")

    # ---------------------- Helpers ----------------------
    def _find_real_node(self, editor_window, key_path):
        ref = editor_window.data
        for k in key_path:
            if isinstance(ref, dict):
                ref = ref.get(k)
            else:
                return None
        return ref

    # ---------------------- Guardar ----------------------
    def save_selected_channels(self, editor_window=None):
        if not editor_window:
            return
        selected_items = [i for i in editor_window.editor_helper.items if getattr(i, 'selected', False)]
        if not selected_items:
            popup_message("EpgNameCorrespondence", "No hay elementos seleccionados.")
            return

        count = 0
        for item in selected_items:
            node = getattr(item, "node", None)
            if isinstance(node, dict) and node.get("item_type") == "channel":
                name = node.get("name")
                if name:
                    parent_node = self._find_real_node(editor_window, editor_window.editor_helper.current_path)
                    if parent_node and "_channels" in parent_node:
                        for c in parent_node["_channels"]:
                            if c is node or c.get("name") == name:
                                # guardamos todo menos name/url básicos
                                self.data[name] = {
                                    k: v for k, v in c.items()
                                    if k not in ("type", "name", "group-title", "url", "_unique_id")
                                }
                                count += 1
        self._save_data()
        popup_message("EpgNameCorrespondence", f"Guardados {count} canales.")

    # ---------------------- Cargar ----------------------
    def load_selected_channels(self, editor_window=None):
        if not editor_window:
            return
        selected_items = [i for i in editor_window.editor_helper.items if getattr(i, 'selected', False)]
        if not selected_items:
            popup_message("EpgNameCorrespondence", "No hay elementos seleccionados.")
            return

        count = 0
        for item in selected_items:
            node = getattr(item, "node", None)
            if isinstance(node, dict) and node.get("item_type") == "channel":
                name = node.get("name")
                if name and name in self.data:
                    parent_node = self._find_real_node(editor_window, editor_window.editor_helper.current_path)
                    if parent_node and "_channels" in parent_node:
                        for c in parent_node["_channels"]:
                            if c is node or c.get("name") == name:
                                for k, v in self.data[name].items():
                                    if k not in ("name", "group-title", "url", "_unique_id"):
                                        c[k] = v
                                count += 1

        editor_window.editor_helper.populate_list()
        popup_message("EpgNameCorrespondence", f"Datos cargados en {count} canales.")

    # ---------------------- Configuración ----------------------
    def _open_plugin_config_menu_(self, parent=None):
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        txt = TextInput(text=str(self.data_file), multiline=False, hint_text="Correspondences JSON file")
        layout.add_widget(txt)

        btn_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        btn_ok = Button(text="OK")
        btn_cancel = Button(text="Cancelar")
        btn_layout.add_widget(btn_ok)
        btn_layout.add_widget(btn_cancel)
        layout.add_widget(btn_layout)

        popup = Popup(title="Configure EpgNameCorrespondence", content=layout, size_hint=(0.7, 0.3))
        btn_ok.bind(on_release=lambda *a: self._do_config(txt.text.strip(), popup))
        btn_cancel.bind(on_release=popup.dismiss)
        popup.open()

    def _do_config(self, filename, popup):
        popup.dismiss()
        if not filename:
            return
        self.data_file = filename
        self._load_data()
        popup_message("EpgNameCorrespondence", f"Usando archivo: {self.data_file}")


    # ---------------------- Edición con refresco y filtro ----------------------
    def edit_correspondences(self, editor_window=None):
        layout = BoxLayout(orientation="vertical", spacing=5, padding=5)

        # TextInput para filtrar
        filter_input = TextInput(
            hint_text="Filter channels by name...",
            size_hint_y=None,
            height=40
        )
        layout.add_widget(filter_input)

        # Scroll + Grid para botones de canales
        scroll = ScrollView(size_hint=(1, 1))
        grid = GridLayout(cols=1, spacing=5, size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        scroll.add_widget(grid)
        layout.add_widget(scroll)

        # Botón de cerrar
        btn_close = Button(text="Close", size_hint_y=None, height=40)
        layout.add_widget(btn_close)

        popup = Popup(title="Edit Correspondences", content=layout, size_hint=(0.7, 0.7))
        btn_close.bind(on_release=popup.dismiss)

        # Función que refresca la lista de canales
        def refresh_list(filter_text=""):
            grid.clear_widgets()
            for name, fields in self.data.items():
                if filter_text.lower() in name.lower():
                    btn = Button(text=name, size_hint_y=None, height=40)
                    btn.bind(on_release=lambda inst, n=name, f=fields: open_editor(n, f))
                    grid.add_widget(btn)

        # Callback para abrir editor de canal
        def open_editor(name, fields):
            self._open_channel_editor(name, fields, on_save_callback=lambda: refresh_list(filter_input.text))

        # Bind para el filtro
        def on_filter_change(instance, value):
            refresh_list(value)

        filter_input.bind(text=on_filter_change)

        # Inicializamos lista
        refresh_list()

        popup.open()


    def _open_channel_editor(self, name, fields, on_save_callback=None):
        """
        Abre el AddChannelDialog para editar una correspondencia de canal.
        Deshabilita 'name' y 'url', evita que la validación bloquee el guardado.
        """
        def on_save(new_data, old_data=None):
            self.data[name] = {k: v for k, v in new_data.items() if k not in ("name", "url")}
            self._save_data()
            if on_save_callback:
                on_save_callback()
            popup_message("EpgNameCorrespondence", f"Data updated for {name}")

        ch_data = {"name": name, **fields, "url": "None"}
        dlg = AddChannelDialog(channel_data=ch_data, on_save=on_save)

        if "name" in dlg.field_edits:
            dlg.field_edits["name"].disabled = True
        if "url" in dlg.field_edits:
            dlg.field_edits["url"].disabled = True

        dlg.open()



    def _save_channel_edit(self, new_data, old_data=None):
        name = new_data.get("name")
        if not name:
            return

        # Actualizamos los datos de correspondencia
        self.data[name] = {k: v for k, v in new_data.items() if k not in ("name", "url")}
        self._save_data()

        # Mensaje de confirmación
        popup_message("EpgNameCorrespondence", f"Datos actualizados para {name}")



# ======================= Registro =======================
plugin_class = EpgNameCorrespondence
