# app/add_channel_dialog_kivy.py
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
import threading
import requests
from io import BytesIO
import os

class AddChannelDialog(Popup):
    FIELD_ICONS = {
        "name": "📺",
        "tvg-id": "🆔",
        "tvg-name": "✏️",
        "tvg-logo": "🖼️",
        "tvg-country": "🌍",
        "tvg-language": "🗣️",
        "tvg-url": "🔗",
        "tvg-rec": "⏺️",
        "tvg-chno": "🔢",
        "url": "🌐"
    }

    FIELD_TOOLTIPS = {
        "name": "Visible channel name",
        "tvg-id": "Unique channel identifier",
        "tvg-name": "Internal EPG name if different",
        "tvg-logo": "Channel logo URL",
        "tvg-country": "Country code (ISO 3166-1 alpha-2)",
        "tvg-language": "Channel language",
        "tvg-url": "Electronic Program Guide URL",
        "tvg-rec": "Recording ID",
        "tvg-chno": "Channel number",
        "url": "Streaming URL of the channel"
    }

    def __init__(self, channel_data=None, dark_mode=False, on_save=None, **kwargs):
        """
        :param channel_data: dict con datos existentes (para editar)
        :param dark_mode: bool
        :param on_save: callback(new_data, old_data) -> None
        """
        super().__init__(**kwargs)
        self.title = "Add/Edit Channel"
        self.size_hint = (0.9, 0.9)
        self.auto_dismiss = False
        self.channel_data = channel_data or {}
        self.all_fields = list(self.FIELD_ICONS.keys())
        self.dark_mode = dark_mode
        self.field_edits = {}
        self.on_save = on_save  # callback al guardar

        # --- Main Layout ---
        self.main_layout = BoxLayout(orientation='horizontal', spacing=10, padding=10)
        self.content = self.main_layout

        # Construir formulario y panel derecho
        self._build_form()
        self._build_logo_and_buttons()

        # Layout responsive
        def update_orientation(instance, value):
            if self.width < 600:
                self.main_layout.orientation = 'vertical'
                self.form_scroll.size_hint = (1, 0.65)
                self.right_layout.size_hint = (1, 0.35)
            else:
                self.main_layout.orientation = 'horizontal'
                self.form_scroll.size_hint = (0.65, 1)
                self.right_layout.size_hint = (0.35, 1)

        self.bind(width=update_orientation)

        # Preview inicial
        logo_url = channel_data.get("tvg-logo") if channel_data else None
        if logo_url:
            self.update_logo_preview(logo_url)

    # ---------------- Formulario scrollable ----------------
    def _build_form(self):
        scroll = ScrollView(size_hint=(0.7, 1))
        form_layout = GridLayout(cols=1, spacing=5, size_hint_y=None)
        form_layout.bind(minimum_height=form_layout.setter('height'))

        for field in self.all_fields:
            row = BoxLayout(orientation='horizontal', spacing=5, size_hint_y=None, height=40)
            icon_label = Label(text=self.FIELD_ICONS.get(field, ""), size_hint=(None, 1), width=30)
            text_label = Label(text=field + ":", size_hint=(None, 1), width=120, halign="right", valign="middle")
            text_label.bind(size=text_label.setter('text_size'))
            edit_field = TextInput(text=self.channel_data.get(field, ""), multiline=False, hint_text=self.FIELD_TOOLTIPS.get(field, ""))
            self.field_edits[field] = edit_field
            row.add_widget(icon_label)
            row.add_widget(text_label)
            row.add_widget(edit_field)
            form_layout.add_widget(row)

            if field == "tvg-logo":
                edit_field.bind(text=self.update_logo_preview)

        scroll.add_widget(form_layout)
        self.main_layout.add_widget(scroll)
        self.form_scroll = scroll

    # ---------------- Panel derecho: logo + botones ----------------
    def _build_logo_and_buttons(self):
        right_layout = BoxLayout(orientation='vertical', spacing=10, size_hint=(0.3, 1))

        # Logo preview
        self.logo_preview = Image(size_hint=(1, 1))
        right_layout.add_widget(self.logo_preview)

        right_layout.add_widget(Label(size_hint_y=None, height=20))  # spacer

        # Botones
        btn_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=80)
        self.ok_button = IconButton(os.path.join("app", "icons", "accept.png"))
        self.cancel_button = IconButton(os.path.join("app", "icons", "cancel.png"))

        btn_layout.add_widget(self.ok_button)
        btn_layout.add_widget(self.cancel_button)
        right_layout.add_widget(btn_layout)

        # Conexiones
        self.ok_button.bind(on_release=self._on_accept)
        self.cancel_button.bind(on_release=self.dismiss)

        self.main_layout.add_widget(right_layout)
        self.right_layout = right_layout

    # ---------------- Logo preview ----------------
    def update_logo_preview(self, instance=None, url_text=None):
        url = ""
        if url_text is not None:
            url = url_text
        elif hasattr(instance, 'text'):
            url = instance.text
        elif isinstance(instance, str):
            url = instance

        if not url.strip():
            self.logo_preview.source = ""
            return

        def download():
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    buf = BytesIO(resp.content)
                    img = CoreImage(buf, ext="png")
                    Clock.schedule_once(lambda dt: setattr(self.logo_preview, 'texture', img.texture))
            except Exception:
                pass

        threading.Thread(target=download, daemon=True).start()

    # ---------------- Aceptar ----------------
    def _on_accept(self, *args):
        name = self.field_edits["name"].text.strip()
        url = self.field_edits["url"].text.strip()
        if not name or not url:
            return

        new_data = {field: self.field_edits[field].text.strip() for field in self.all_fields}

        # Llamar callback si hay
        if callable(self.on_save):
            self.on_save(new_data, self.channel_data if self.channel_data else None)

        self.dismiss()


# ---------------- Botón con icono y fondo ----------------
class IconButton(ButtonBehavior, BoxLayout):
    def __init__(self, icon_path, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.padding = 4
        self.spacing = 5

        # Fondo estético
        with self.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.25, 0.25, 0.25, 1)
            self.bg_rect = RoundedRectangle(radius=[10])

        self.bind(pos=self._update_bg, size=self._update_bg)

        self.img = Image(source=icon_path)
        self.img.color = (0.2, 0.6, 0.9, 1)
        self.add_widget(self.img)

    def _update_bg(self, *args):
        if hasattr(self, "bg_rect"):
            self.bg_rect.pos = self.pos
            self.bg_rect.size = self.size
