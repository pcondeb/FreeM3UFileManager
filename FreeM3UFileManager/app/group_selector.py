# app/group_selector.py
from kivy.uix.treeview import TreeView, TreeViewLabel
from kivy.properties import ObjectProperty

class GroupSelector(TreeView):
    """
    Widget to select a group from the M3U data structure.
    Adds a "Top-level" root node representing the parent group.
    """
    selected_path = ObjectProperty(None)

    def __init__(self, data, **kwargs):
        super().__init__(hide_root=True, **kwargs)
        self.data = data
        self.selected_path = []
        self.root_item = None  # store reference to the root node
        self.populate_tree()

    def populate_tree(self):
        self.clear_widgets()
        # Root node
        self.root_item = TreeViewLabel(text="Top-level")
        self.root_item.path = []  # empty path represents root
        self.add_node(self.root_item)
        self._add_groups(self.data, parent_node=self.root_item, path=[])
        self.root_item.is_open = True
        # Selection binding
        self.bind(selected_node=self.on_select_node)

    def _add_groups(self, data_dict, parent_node=None, path=[]):
        for key, value in data_dict.items():
            if key == "_channels":
                continue
            node = TreeViewLabel(text=key)
            node.path = path + [key]
            self.add_node(node, parent_node)
            # Recursive
            if isinstance(value, dict):
                self._add_groups(value, node, path + [key])

    def on_select_node(self, instance, value):
        if hasattr(value, "path"):
            self.selected_path = value.path

    def get_selected_path(self):
        return self.selected_path

    def expand_all(self):
        """Expands all nodes starting from root_item"""
        if not self.root_item:
            return

        def _expand(node):
            node.is_open = True
            # Iterate over node children
            if hasattr(node, 'nodes'):
                for child in node.nodes:
                    _expand(child)

        _expand(self.root_item)
