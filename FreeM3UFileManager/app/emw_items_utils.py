# app/emw_items_utils.py
# -*- coding: utf-8 -*-
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from app.add_channel_dialog import AddChannelDialog
from app.group_selector import GroupSelector
import copy

def add_channel(editor_helper):
    def on_save(new_data, old_data=None):
        current_data = editor_helper.get_current_data()
        new_data['group-title'] = "/".join(editor_helper.current_path) if editor_helper.current_path else ""
        if isinstance(current_data, dict):
            if "_channels" not in current_data:
                current_data["_channels"] = []
            current_data["_channels"].append(new_data)
        elif isinstance(current_data, list):
            current_data.append(new_data)
        editor_helper.populate_list()

    dlg = AddChannelDialog(channel_data=None, on_save=on_save)
    dlg.open()

def edit_channel(editor_helper, channel):
    def on_save(new_data, old_data):
            if old_data:  # Edit existing
                old_data.update(new_data)  # Update the data in the dict
            else:  # Create new
                data_ref = editor_helper.get_current_data()
                if isinstance(data_ref, dict):
                    if "_channels" not in data_ref:
                        data_ref["_channels"] = []
                    data_ref["_channels"].append(new_data)
                elif isinstance(data_ref, list):
                    data_ref.append(new_data)
            editor_helper.populate_list()  # Refresh UI

    dlg = AddChannelDialog(channel_data=channel, on_save=on_save)
    dlg.open()


def add_group(editor_helper):
    content = BoxLayout(orientation="vertical", spacing=10, padding=10)
    input_field = TextInput(hint_text="Group name", multiline=False, size_hint_y=None, height=40)
    content.add_widget(input_field)

    btn_layout = BoxLayout(size_hint_y=None, height=40, spacing=5)
    ok_btn = Button(text="OK")
    cancel_btn = Button(text="Cancel")
    btn_layout.add_widget(ok_btn)
    btn_layout.add_widget(cancel_btn)
    content.add_widget(btn_layout)

    from kivy.uix.popup import Popup
    popup = Popup(title="New Group", content=content, size_hint=(0.4, 0.4))

    def on_ok(*args):
        name = input_field.text.strip()
        if not name:
            return
        current_data = editor_helper.get_current_data()
        if isinstance(current_data, dict):
            if name not in current_data:
                current_data[name] = {"_channels": []}
        elif isinstance(current_data, list):
            current_data.append({name: {"_channels": []}})
        editor_helper.populate_list()
        popup.dismiss()

    ok_btn.bind(on_release=on_ok)
    cancel_btn.bind(on_release=lambda *_: popup.dismiss())
    popup.open()

def rename_group(editor_helper, group_dict):
    if not editor_helper.current_path:
        # group in root, current_path empty
        parent_ref = editor_helper.data_root
    else:
        # walk current_path until the second-to-last element to get parent dict
        parent_ref = editor_helper.data_root
        for key in editor_helper.current_path:
            parent_ref = parent_ref[key]

    old_key = group_dict['name']

    # Open popup
    layout = BoxLayout(orientation="vertical", spacing=10, padding=10)
    input_name = TextInput(text=old_key, multiline=False)
    save_button = Button(text="Save", size_hint_y=None, height=40)
    cancel_button = Button(text="Cancel", size_hint_y=None, height=40)

    def save_and_close(*args):
        new_name = input_name.text.strip()
        if not new_name or new_name == old_key:
            popup.dismiss()
            return

        # Rename key in parent dict
        parent_ref[new_name] = parent_ref.pop(old_key)

        # Update all group-title of subchannels
        full_path = (editor_helper.current_path if editor_helper.current_path else []) + [new_name]
        update_group_title_recursive(parent_ref[new_name], full_path)

        editor_helper.populate_list()
        popup.dismiss()

    save_button.bind(on_release=save_and_close)
    cancel_button.bind(on_release=lambda *args: popup.dismiss())

    layout.add_widget(input_name)
    layout.add_widget(save_button)
    layout.add_widget(cancel_button)

    popup = Popup(title="Rename group", content=layout, size_hint=(0.6, 0.4))
    popup.open()




def _ensure_unique_group_name(parent_dict, desired_name):
    """
    Ensure that the group name is unique in parent_dict.
    """
    if desired_name not in parent_dict:
        return desired_name
    i = 1
    new_name = f"{desired_name} ({i})"
    while new_name in parent_dict:
        i += 1
        new_name = f"{desired_name} ({i})"
    return new_name


# ---------------------------
# REMOVE FUNCTIONS
# ---------------------------
def remove_channel(editor_helper, channel_data):
    """
    Remove a channel from the current level.
    Search by identity, _unique_id or (name, url)
    """
    current_data = editor_helper.get_current_data()
    if not isinstance(current_data, dict):
        return
    channels = current_data.get("_channels", [])
    if not isinstance(channels, list):
        return

    # 1) search by identity
    for i, ch in enumerate(channels):
        if ch is channel_data:
            channels.pop(i)
            editor_helper.populate_list()
            return

    # 2) search by _unique_id
    uid = channel_data.get("_unique_id") if isinstance(channel_data, dict) else None
    if uid:
        for i, ch in enumerate(channels):
            if isinstance(ch, dict) and ch.get("_unique_id") == uid:
                channels.pop(i)
                editor_helper.populate_list()
                return

    # 3) fallback: by (name, url)
    name, url = channel_data.get("name"), channel_data.get("url")
    for i, ch in enumerate(channels):
        if ch.get("name") == name and ch.get("url") == url:
            channels.pop(i)
            editor_helper.populate_list()
            return


def remove_group(editor_helper, group_key):
    """
    Remove a subgroup identified by group_key from the current level.
    """
    current_data = editor_helper.get_current_data()
    if not isinstance(current_data, dict):
        return
    if group_key in current_data:
        current_data.pop(group_key, None)
        editor_helper.populate_list()


def remove_channel_recursive(editor_helper, channel_data):
    """
    Remove a channel recursively across the entire JSON.
    """
    def recurse(ref):
        if isinstance(ref, dict):
            ch_list = ref.get("_channels", [])
            if channel_data in ch_list:
                ch_list.remove(channel_data)
            for k, v in ref.items():
                if k != "_channels":
                    recurse(v)
        elif isinstance(ref, list):
            if channel_data in ref:
                ref.remove(channel_data)
    recurse(editor_helper.root_data)
    editor_helper.populate_list()


def remove_group_recursive(editor_helper, group_key):
    """
    Remove a group recursively across the entire JSON.
    """
    def recurse(ref):
        if isinstance(ref, dict):
            if group_key in ref:
                del ref[group_key]
                return True
            for k, v in ref.items():
                if k != "_channels":
                    if recurse(v):
                        return True
        return False
    recurse(editor_helper.root_data)
    editor_helper.populate_list()


# -----------------------
# Helper functions
# -----------------------
def collect_items(selected_items):
    """
    Return a list of tuples (type, data) of the items to process.
    type: "channel" or "group"
    data: channel dict or (key, group dict)
    """
    items = []
    for item in selected_items:
        node = getattr(item, 'node', None)
        if not node:
            continue
        if getattr(item, 'item_type', None) == "channel":
            items.append(("channel", item.data))
        elif getattr(item, 'item_type', None) == "group":
            items.append(("group", item.data))
    return items


def update_group_title_recursive(group_dict, path_so_far):
    if not isinstance(group_dict, dict):
        return

    # update direct channels
    for ch in group_dict.get("_channels", []):
        if isinstance(ch, dict):
            ch['group-title'] = "/".join(path_so_far) if path_so_far else ""

    # walk subgroups
    for k, v in group_dict.items():
        if k != "_channels" and isinstance(v, dict):
            update_group_title_recursive(v, path_so_far + [k])


# -----------------------
# Destination group selection
# -----------------------
def select_destination_group(callback, editor_helper, emw_data):
    """
    Open a GroupSelector in a Popup and call callback(ref) on close.
    ref will be None if canceled.
    """
    layout = BoxLayout(orientation='vertical', spacing=5, padding=5)
    selector = GroupSelector(emw_data)
    layout.add_widget(selector)

    buttons = BoxLayout(size_hint_y=None, height=40, spacing=5)
    ok_btn = Button(text="OK")
    cancel_btn = Button(text="Cancel")
    buttons.add_widget(ok_btn)
    buttons.add_widget(cancel_btn)
    layout.add_widget(buttons)

    popup = Popup(title="Select Destination Group", content=layout,
                  size_hint=(0.8, 0.8))

    def on_ok(instance):
        path = selector.get_selected_path()
        ref = emw_data
        for key in path:
            ref = ref[key]
        if "_channels" not in ref:
            ref["_channels"] = []

        popup.dismiss()

        info = {
            "ref": ref,
            "path": path,
            "current_name": path[-1] if path else "",
            "parent_name": path[-2] if len(path) > 1 else "",
            "parent_path": "/".join(path[:-1]) if len(path) > 1 else ""
        }
        callback(info)

    def on_cancel(instance):
        popup.dismiss()
        callback(None)

    ok_btn.bind(on_release=on_ok)
    cancel_btn.bind(on_release=on_cancel)
    popup.open()


# -----------------------
# Copy items
# -----------------------
def copy_items(editor_helper, editor_main_window=None):
    selected_items = [i for i in editor_helper.items if getattr(i, 'selected', False)]
    if not selected_items:
        if editor_main_window:
            Popup(title="Warning",
                  content=Label(text="No items selected."),
                  size_hint=(0.5, 0.3)).open()
        return

    def process_copy(target_info):
        if target_info is None:
            return

        target_ref = target_info["ref"]
        parent_path = target_info["parent_path"]
        current_name = target_info["current_name"]

        items_to_process = collect_items(selected_items)

        for item_type, data in items_to_process:
            if item_type == "channel":
                path = list(filter(None, [parent_path, current_name]))
                data['group-title'] = "/".join(path) if path else ""
                target_ref["_channels"].append(data.copy())
            elif item_type == "group":
                key = data['name']
                children = data['children']
                # ensure unique name
                new_key = _ensure_unique_group_name(target_ref, key) if editor_main_window else key
                target_ref[new_key] = copy.deepcopy(children)

                full_path = list(filter(None, parent_path.split("/")))
                if current_name:
                    full_path.append(current_name)
                full_path.append(new_key)

                update_group_title_recursive(target_ref[new_key], full_path)

        editor_helper.populate_list()

    select_destination_group(process_copy, editor_helper, editor_main_window.data)


# -----------------------
# Move items
# -----------------------
def move_items(editor_helper, editor_main_window=None):
    selected_items = [i for i in editor_helper.items if getattr(i, 'selected', False)]
    if not selected_items:
        if editor_main_window:
            Popup(title="Warning",
                  content=Label(text="No items selected."),
                  size_hint=(0.5, 0.3)).open()
        return

    def process_move(target_info):
        if target_info is None:
            return

        target_ref = target_info["ref"]
        parent_path = target_info["parent_path"]
        current_name = target_info["current_name"]

        items_to_process = collect_items(selected_items)

        for item_type, data in items_to_process:
            if item_type == "channel":
                path = list(filter(None, [parent_path, current_name]))
                data['group-title'] = "/".join(path) if path else ""
                target_ref["_channels"].append(data)
                remove_channel(editor_helper, data)
            elif item_type == "group":
                key = data['name']
                value = data['children']
                new_key = _ensure_unique_group_name(target_ref, key) if editor_main_window else key
                target_ref[new_key] = copy.deepcopy(value)
                remove_group(editor_helper, key)

                full_path = list(filter(None, parent_path.split("/")))
                if current_name:
                    full_path.append(current_name)
                full_path.append(new_key)

                update_group_title_recursive(target_ref[new_key], full_path)

        editor_helper.populate_list()

    select_destination_group(process_move, editor_helper, editor_main_window.data)
