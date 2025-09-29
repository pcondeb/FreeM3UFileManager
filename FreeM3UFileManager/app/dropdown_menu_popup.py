# app/dropdown_menu_popup.py
# -*- coding: utf-8 -*-
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from functools import partial

# ---------------------- Menu items ----------------------

class MenuItem(Button):
    """Item that executes a function"""
    def __init__(self, name, callback, popup_ref, **kwargs):
        super().__init__(text=name, size_hint_y=None, height=40, **kwargs)
        self.callback = callback
        self.popup_ref = popup_ref
        self.bind(on_release=self.on_execute)

    def on_execute(self, *args):
        self.callback()
        # close only this popup
        self.popup_ref.dismiss()


class SubMenuItem(Button):
    """Item that opens a submenu"""
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
    """Item to go back to the previous menu"""
    def __init__(self, parent_structure, root_structure, title="Back", **kwargs):
        super().__init__(text="< Back", size_hint_y=None, height=40, **kwargs)
        self.parent_structure = parent_structure
        self.root_structure = root_structure
        self.title = title
        self.bind(on_release=self.go_back)

    def go_back(self, *args):
        self.dismiss_current()
        # Open the parent menu popup
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
    """Item to close the entire menu from the root level"""
    def __init__(self, popup_ref, **kwargs):
        super().__init__(text="Close Menu", size_hint_y=None, height=40, **kwargs)
        self.popup_ref = popup_ref
        self.bind(on_release=self.close_all)

    def close_all(self, *args):
        # close all active popups
        for p in DropDownMenuPopup._active_popups[:]:
            p.dismiss()


# ---------------------- Menu popup ----------------------

class DropDownMenuPopup(Popup):
    """Popup with vertical BoxLayout that generates custom items"""
    _active_popups = []

    def __init__(self, structure, root_structure=None, parent_structure=None, title="Menu", **kwargs):
        super().__init__(title=title, size_hint=(0.8, 0.8), **kwargs)
        self.structure = structure
        self.root_structure = root_structure or structure
        self.parent_structure = parent_structure

        # register active popup
        DropDownMenuPopup._active_popups.append(self)

        self.layout = BoxLayout(orientation='vertical', spacing=5, padding=5, size_hint_y=None)
        self.layout.bind(minimum_height=self.layout.setter('height'))

        self.build_menu()
        self.content = self.layout

        if parent_structure:
            # Show BackItem if there is a real parent menu (not root)
            back_item = BackItem(parent_structure=parent_structure, root_structure=self.root_structure, title="Menu")
            self.layout.add_widget(back_item, index=0)
        else:
            # Root level → add option to close menu
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
        # when closing this popup, remove it from the active list
        if self in DropDownMenuPopup._active_popups:
            DropDownMenuPopup._active_popups.remove(self)
        super().dismiss(*args, **kwargs)
