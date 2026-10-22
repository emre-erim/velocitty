"""The icons come from xapp-symbolic-icons. Where that isn't installed (Ubuntu, Arch without
the AUR package), each missing icon is linked to the matching icon of the icon themes that
are there, so that no button is left blank."""

import os

from gi.repository import GLib, Gtk

ICONS = [
    "appearance", "computer", "edit-clear", "emblem-system", "go-down", "go-next", "go-up",
    "input-mouse", "list-drag-handle", "open-menu", "pan-up", "tab-new", "user-bookmarks",
    "utilities-terminal", "view-restore", "weather-clear-night", "weather-clear", "window-close",
    "zoom-in", "zoom-out",
]
# Names the usual themes give some of them
ALIASES = {"appearance": ["preferences-desktop-appearance", "applications-graphics"]}
THEMES = ("Adwaita", "hicolor", "Yaru", "breeze", "Papirus")


def find_icon(roots, name):
    for root in roots:
        for theme in THEMES:
            top = os.path.join(root, theme)
            if not os.path.isdir(top):
                continue
            for folder, _dirs, files in os.walk(top):
                if name + ".svg" in files:
                    return os.path.join(folder, name + ".svg")
    return None


def install_fallback_icons(display):
    theme = Gtk.IconTheme.get_for_display(display)
    missing = [name for name in ICONS if not theme.has_icon("xsi-%s-symbolic" % name)]
    if not missing:
        return
    target = os.path.join(GLib.get_user_cache_dir(), "velocitty", "icons")
    os.makedirs(target, exist_ok=True)
    roots = [path for path in theme.get_search_path() if os.path.isdir(path)]
    for name in missing:
        link = os.path.join(target, "xsi-%s-symbolic.svg" % name)
        if os.path.exists(link):
            continue
        for candidate in [name] + ALIASES.get(name, []):
            source = find_icon(roots, candidate + "-symbolic")
            if source:
                try:
                    os.symlink(source, link)
                except OSError:
                    pass
                break
    theme.add_search_path(target)
