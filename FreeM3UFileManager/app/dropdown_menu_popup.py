# app/dropdown_menu_popup.py
# -*- coding: utf-8 -*-
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from functools import partial

# ---------------------- Items del menú ----------------------

class MenuItem(Button):
    """Item que ejecuta una función"""
    def __init__(self, name, callback, popup_ref, **kwargs):
        super().__init__(text=name, size_hint_y=None, height=40, **kwargs)
        self.callback = callback
        self.popup_ref = popup_ref
        self.bind(on_release=self.on_execute)

    def on_execute(self, *args):
        self.callback()
        # cerrar solo este popup
        self.popup_ref.dismiss()


class SubMenuItem(Button):
    """Item que abre un submenú"""
    def __init__(self, name, submenu_structure, root_structure, parent_structure, **kwargs):
        super().__init__(text=f"> {name}", size_hint_y=None, height=40, **kwargs)
        self.submenu_structure = submenu_structure
        self.root_structure = root_structure
        self.parent_structure = parent_structure
        self.bind(on_release=self.open_submenu)

    def open_submenu(self, *args):
        DropDownMenuPopup(
            self.submenu_structure,
            root_structure=self.root_structure,
            parent_structure=self.parent_structure,
            title=self.text
        ).open()


class BackItem(Button):
    """Item para volver al menú anterior"""
    def __init__(self, parent_structure, root_structure, title="Volver", **kwargs):
        super().__init__(text="< Back", size_hint_y=None, height=40, **kwargs)
        self.parent_structure = parent_structure
        self.root_structure = root_structure
        self.title = title
        self.bind(on_release=self.go_back)

    def go_back(self, *args):
        self.dismiss_current()
        # Abrir el popup del menú padre
        DropDownMenuPopup(
            self.parent_structure,
            root_structure=self.root_structure,
            parent_structure=None if self.parent_structure == self.root_structure else self.root_structure,
            title=self.title
        ).open()

    def dismiss_current(self):
        popup = self.get_parent_popup()
        if popup:
            popup.dismiss()

    def get_parent_popup(self):
        parent = self.parent
        while parent:
            if isinstance(parent, Popup):
                return parent
            parent = parent.parent
        return None


class CloseMenuItem(Button):
    """Item para cerrar el menú completo desde el nivel raíz"""
    def __init__(self, popup_ref, **kwargs):
        super().__init__(text="Close Menu", size_hint_y=None, height=40, **kwargs)
        self.popup_ref = popup_ref
        self.bind(on_release=self.close_all)

    def close_all(self, *args):
        # cerrar todos los popups activos
        for p in DropDownMenuPopup._active_popups[:]:
            p.dismiss()


# ---------------------- Popup del menú ----------------------

class DropDownMenuPopup(Popup):
    """Popup con BoxLayout vertical que genera items personalizados"""
    _active_popups = []

    def __init__(self, structure, root_structure=None, parent_structure=None, title="Menú", **kwargs):
        super().__init__(title=title, size_hint=(0.8, 0.8), **kwargs)
        self.structure = structure
        self.root_structure = root_structure or structure
        self.parent_structure = parent_structure

        # registrar popup activo
        DropDownMenuPopup._active_popups.append(self)

        self.layout = BoxLayout(orientation='vertical', spacing=5, padding=5, size_hint_y=None)
        self.layout.bind(minimum_height=self.layout.setter('height'))

        self.build_menu()
        self.content = self.layout

        if parent_structure:
            # Mostrar BackItem si hay un menú padre real (no raíz)
            back_item = BackItem(parent_structure=parent_structure, root_structure=self.root_structure, title="Menú")
            self.layout.add_widget(back_item, index=0)
        else:
            # Nivel raíz → añadir opción para cerrar menú
            self.layout.add_widget(CloseMenuItem(popup_ref=self), index=0)

    def build_menu(self):
        for name, value in self.structure.items():
            if callable(value):
                self.layout.add_widget(MenuItem(name, value, popup_ref=self))
            elif isinstance(value, dict):
                self.layout.add_widget(SubMenuItem(
                    name,
                    value,
                    root_structure=self.root_structure,
                    parent_structure=self.structure
                ))

    def dismiss(self, *args, **kwargs):
        # al cerrar este popup, eliminarlo de la lista de activos
        if self in DropDownMenuPopup._active_popups:
            DropDownMenuPopup._active_popups.remove(self)
        super().dismiss(*args, **kwargs)
