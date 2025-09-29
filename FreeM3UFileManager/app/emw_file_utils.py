# app/emw_file_utils.py
# -*- coding: utf-8 -*-
import os, json, re

def load_file(file_path, is_new):
    if os.path.exists(file_path) and not is_new:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content.startswith("{"):
                    return json.loads(content)
                else:
                    return parse_m3u_to_dict(file_path)
        except Exception as e:
            raise RuntimeError(f"Error loading file: {e}")
    return {}

def parse_m3u_to_dict(file_path):
    tree = {}
    current_channel = None
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#EXTINF:"):
                attrs = dict(re.findall(r'([\w-]+)="(.*?)"', line))
                group_title = attrs.get("group-title", "") or ""
                name = line.rsplit(",", 1)[-1].strip() if "," in line else attrs.get("tvg-id", "") or "Unknown"
                current_channel = {
                    "name": name,
                    "group-title": group_title,
                    "url": "",
                    "tvg-id": attrs.get("tvg-id", ""),
                    "tvg-name": attrs.get("tvg-name", ""),
                    "tvg-logo": attrs.get("tvg-logo", ""),
                    "tvg-shift": attrs.get("tvg-shift", ""),
                    "tvg-url": attrs.get("tvg-url", ""),
                    "radio": attrs.get("radio", ""),
                    "catchup": attrs.get("catchup", ""),
                    "catchup-source": attrs.get("catchup-source", ""),
                    "catchup-days": attrs.get("catchup-days", ""),
                }
            elif current_channel:
                current_channel["url"] = line
                if current_channel["group-title"] == "":
                    tree.setdefault("_channels", []).append(current_channel)
                else:
                    parts = current_channel["group-title"].split("/")
                    ref = tree
                    for part in parts:
                        if part not in ref:
                            ref[part] = {"_channels": []}
                        ref = ref[part]
                    ref["_channels"].append(current_channel)
                current_channel = None
    return tree

def write_m3u_recursive(ref, f):
    if isinstance(ref, dict):
        for k, v in ref.items():
            if k == "_channels":
                for ch in v:
                    f.write(channel_to_extinf(ch) + "\n")
                    f.write(ch.get("url", "") + "\n")
            else:
                write_m3u_recursive(v, f)
    elif isinstance(ref, list):
        for ch in ref:
            f.write(channel_to_extinf(ch) + "\n")
            f.write(ch.get("url", "") + "\n")

def channel_to_extinf(ch):
    attrs = []
    for key in ["tvg-id", "tvg-name", "tvg-logo", "tvg-url", "tvg-shift", "radio", "catchup", "catchup-source", "catchup-days", "group-title"]:
        val = ch.get(key)
        if val:
            attrs.append(f'{key}="{val}"')
    return f'#EXTINF:-1 {" ".join(attrs)},{ch.get("name","")}'
