# app/diff_dialog.py
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.treeview import TreeView, TreeViewLabel
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock
from copy import deepcopy

class DiffDialog(Popup):
    def __init__(self, old_data, new_data, **kwargs):
        super().__init__(**kwargs)
        self.title = "Comparar cambios"
        self.size_hint = (0.95, 0.95)
        self.auto_dismiss = False
        self.result = None  # "accept", "review", "cancel"

        self.old_data = deepcopy(old_data)
        self.new_data = deepcopy(new_data)

        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)

        title_label = Label(text="Comparación de listas de grupos y canales", size_hint_y=None, height=30)
        layout.add_widget(title_label)

        # Árbol de diferencias
        self.tree = TreeView(hide_root=True)
        layout.add_widget(self.tree)

        self.populate_tree("", self.old_data, self.new_data, parent_node=None)

        # Botones
        btn_layout = BoxLayout(size_hint_y=None, height=50, spacing=5)
        btn_accept = Button(text="✅ Aceptar cambios")
        btn_review = Button(text="🔍 Revisar después")
        btn_cancel = Button(text="❌ Cancelar")

        btn_accept.bind(on_release=lambda inst: self._close_with("accept"))
        btn_review.bind(on_release=lambda inst: self._close_with("review"))
        btn_cancel.bind(on_release=lambda inst: self._close_with("cancel"))

        btn_layout.add_widget(btn_accept)
        btn_layout.add_widget(btn_review)
        btn_layout.add_widget(btn_cancel)

        layout.add_widget(btn_layout)

        self.add_widget(layout)

    def _close_with(self, action):
        self.result = action
        self.dismiss()

    def populate_tree(self, path, old, new, parent_node):
        """Rellena el árbol con grupos y canales"""

        # Si ambos son listas → canales
        if isinstance(old, list) or isinstance(new, list):
            old_list = old if isinstance(old, list) else []
            new_list = new if isinstance(new, list) else []
            self.populate_channels(parent_node, old_list, new_list)
            return

        # Si ambos son dicts → grupos
        if isinstance(old, dict) or isinstance(new, dict):
            old_keys = set(old.keys()) if isinstance(old, dict) else set()
            new_keys = set(new.keys()) if isinstance(new, dict) else set()
            all_keys = sorted(old_keys | new_keys)

            for key in all_keys:
                old_val = old.get(key) if isinstance(old, dict) else None
                new_val = new.get(key) if isinstance(new, dict) else None

                if key == "_channels":
                    self.populate_tree(f"{path}/{key}", old_val, new_val, parent_node)
                else:
                    node = TreeViewLabel(text=key)
                    node.old_val = old_val
                    node.new_val = new_val
                    if parent_node:
                        self.tree.add_node(node, parent_node)
                    else:
                        self.tree.add_node(node)
                    self.populate_tree(f"{path}/{key}", old_val, new_val, node)

    def populate_channels(self, parent_node, old_channels, new_channels):
        old_map = {c.get("name",""): c for c in old_channels if isinstance(c, dict)}
        new_map = {c.get("name",""): c for c in new_channels if isinstance(c, dict)}
        all_names = sorted(set(old_map.keys()) | set(new_map.keys()))

        for name in all_names:
            old_c = old_map.get(name)
            new_c = new_map.get(name)
            text = name
            if old_c and not new_c:
                text += " ❌ Eliminado"
            elif new_c and not old_c:
                text += " ✅ Nuevo"
            else:
                diffs = [f"{k}: {old_c.get(k)} → {new_c.get(k)}" for k in new_c.keys() if k != "name" and old_c.get(k)!=new_c.get(k)]
                if diffs:
                    text += " 🟡 Modificado"
            node = TreeViewLabel(text=text)
            node.channel_data = new_c or old_c
            if parent_node:
                self.tree.add_node(node, parent_node)
            else:
                self.tree.add_node(node)

