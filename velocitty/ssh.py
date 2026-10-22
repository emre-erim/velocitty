"""The SSH address book: hosts saved here and the hosts of ~/.ssh/config, in a panel beside the terminals."""

import glob
import json
import os
import shlex

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk, Pango

from velocitty import GETTEXT_DOMAIN
from velocitty.i18n import l10n

_ = l10n(GETTEXT_DOMAIN)

FILE = os.path.join(GLib.get_user_state_dir(), "velocitty", "ssh.json")
SSH_CONFIG = os.path.expanduser("~/.ssh/config")
FIELDS = ("name", "host", "user", "port", "key", "group", "options")


# -- the hosts -------------------------------------------------------------

def command_for(host):
    """The ssh command line for a host."""
    if host.get("alias"):
        return "ssh " + shlex.quote(host["alias"])
    argv = ["ssh"]
    if host.get("port") and str(host["port"]) != "22":
        argv += ["-p", str(host["port"])]
    if host.get("key"):
        argv += ["-i", os.path.expanduser(host["key"])]
    extra = []
    if host.get("options"):
        try:
            extra = shlex.split(host["options"])
        except ValueError:
            extra = host["options"].split()
    target = host["host"]
    if host.get("user"):
        target = host["user"] + "@" + target
    return " ".join(shlex.quote(arg) for arg in argv + extra + [target])


def address_of(host):
    """user@host:port, as it is shown."""
    text = host.get("host") or host.get("alias") or ""
    if host.get("user"):
        text = host["user"] + "@" + text
    if host.get("port") and str(host["port"]) != "22":
        text += ":%s" % host["port"]
    return text


def read_ssh_config(path=SSH_CONFIG, seen=None):
    """The hosts named in an ssh config file and the files it includes. Patterns (*, ?, !)
    are left out: they are rules, not hosts."""
    seen = seen if seen is not None else set()
    path = os.path.realpath(path)
    if path in seen or not os.path.isfile(path):
        return []
    seen.add(path)
    hosts, current = [], []
    try:
        with open(path, errors="replace") as handle:
            lines = handle.readlines()
    except OSError:
        return []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.replace("=", " ", 1).split(None, 1)
        if len(parts) < 2:
            continue
        key, value = parts[0].lower(), parts[1].strip().strip('"')
        if key == "include":
            for pattern in shlex.split(value):
                pattern = os.path.expanduser(pattern)
                if not os.path.isabs(pattern):
                    pattern = os.path.join(os.path.expanduser("~/.ssh"), pattern)
                for included in sorted(glob.glob(pattern)):
                    hosts += read_ssh_config(included, seen)
        elif key == "host":
            current = [{"alias": name, "name": name, "group": _("SSH Config")}
                       for name in value.split() if not any(c in name for c in "*?!")]
            hosts += current
        elif key == "match":
            current = []
        elif key in ("hostname", "user", "port"):
            field = {"hostname": "host"}.get(key, key)
            for host in current:
                host.setdefault(field, value)
    for host in hosts:
        host.setdefault("host", host["alias"])
    return hosts


class SshHosts(GObject.Object):
    """The hosts saved in the address book."""

    __gsignals__ = {"changed": (GObject.SignalFlags.RUN_LAST, None, ())}

    def __init__(self):
        super().__init__()
        self.entries = self.load()

    def load(self):
        try:
            with open(FILE) as handle:
                entries = json.load(handle)
            return [{key: str(entry.get(key) or "") for key in FIELDS}
                    for entry in entries if isinstance(entry, dict) and entry.get("host")]
        except (OSError, ValueError, TypeError):
            return []

    def save(self):
        try:
            os.makedirs(os.path.dirname(FILE), exist_ok=True)
            temporary = FILE + ".tmp"
            with open(temporary, "w") as handle:
                os.chmod(temporary, 0o600)
                json.dump(self.entries, handle, indent=1)
            os.replace(temporary, FILE)
        except OSError:
            pass
        self.emit("changed")

    def put(self, old, new):
        """Add new, or replace old with it."""
        if old is not None and old in self.entries:
            self.entries[self.entries.index(old)] = new
        else:
            self.entries.append(new)
        self.save()

    def remove(self, entry):
        if entry in self.entries:
            self.entries.remove(entry)
            self.save()


# -- the page --------------------------------------------------------------

# -- the panel -------------------------------------------------------------

def parse_address(text):
    """"user@host:port" (any part but the host can be left out) into its parts."""
    text = text.strip()
    user, _at, rest = text.rpartition("@")
    host, port = rest, ""
    if rest.startswith("["):   # [ipv6]:port
        end = rest.find("]")
        host, port = rest[1:end], rest[end + 2:] if rest[end + 1:end + 2] == ":" else ""
    elif rest.count(":") == 1:
        host, port = rest.split(":")
    return user, host, port


def join_address(host):
    text = host.get("host") or ""
    if ":" in text:
        text = "[%s]" % text
    if host.get("user"):
        text = host["user"] + "@" + text
    if host.get("port") and str(host["port"]) != "22":
        text += ":%s" % host["port"]
    return text


class HostRow(Gtk.ListBoxRow):
    """A host: click connects. The ⋮ button and right click give the other choices."""

    def __init__(self, panel, host):
        super().__init__(css_classes=["ssh-host"])
        self.host = host
        saved = host.get("saved") is not None

        title = Gtk.Label(label=host["name"], xalign=0, css_classes=["ssh-host-name"],
                          ellipsize=Pango.EllipsizeMode.END)
        subtitle = address_of(host)
        if host.get("alias") and host.get("host") != host.get("alias"):
            subtitle = "%s · %s" % (host["alias"], subtitle)
        address = Gtk.Label(label=subtitle, xalign=0, css_classes=["dim-label", "caption"],
                            ellipsize=Pango.EllipsizeMode.MIDDLE)
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
        text.append(title)
        text.append(address)

        # "Connect →" shows while the pointer is over the row, so it is clear what a click does
        hint = Gtk.Label(label=_("Connect") + " →", css_classes=["ssh-connect-hint", "caption"])
        self.hint = Gtk.Revealer(child=hint, transition_type=Gtk.RevealerTransitionType.SLIDE_LEFT,
                                 valign=Gtk.Align.CENTER)

        actions = Gio.SimpleActionGroup()
        for name, handler in (("connect", lambda: panel.connect_to(host)),
                              ("split", lambda: panel.connect_to(host, split=True)),
                              ("edit", lambda: panel.edit(host["saved"])),
                              ("remove", lambda: panel.confirm_remove(host["saved"])),
                              ("save", lambda: panel.edit(None, template=host)),
                              ("copy", lambda: panel.copy_command(host))):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda _a, _p, h=handler: h())
            actions.add_action(action)
        self.insert_action_group("host", actions)

        menu = Gio.Menu()
        section = Gio.Menu()
        section.append(_("Connect in a New Tab"), "host.connect")
        section.append(_("Connect in a Split"), "host.split")
        section.append(_("Copy the ssh Command"), "host.copy")
        menu.append_section(None, section)
        section = Gio.Menu()
        if saved:
            section.append(_("Edit…"), "host.edit")
            section.append(_("Remove"), "host.remove")
        else:
            section.append(_("Save to the Address Book…"), "host.save")
        menu.append_section(None, section)
        self.menu = menu
        more = Gtk.MenuButton(icon_name="view-more-symbolic", menu_model=menu, valign=Gtk.Align.CENTER,
                              css_classes=["flat", "circular"], tooltip_text=_("More"))

        box = Gtk.Box(spacing=10, margin_start=10, margin_end=4, margin_top=6, margin_bottom=6)
        box.append(Gtk.Image(icon_name="network-server-symbolic", css_classes=["dim-label"]))
        box.append(text)
        box.append(self.hint)
        box.append(more)
        self.set_child(box)
        self.set_tooltip_text(_("Click to connect to %s") % address_of(host))

        motion = Gtk.EventControllerMotion()
        motion.connect("enter", lambda *_: self.hint.set_reveal_child(True))
        motion.connect("leave", lambda *_: self.hint.set_reveal_child(False))
        self.add_controller(motion)
        click = Gtk.GestureClick(button=3)
        click.connect("pressed", self.on_right_click)
        self.add_controller(click)

    def on_right_click(self, gesture, n_press, x, y):
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        popover = Gtk.PopoverMenu.new_from_model(self.menu)
        popover.set_parent(self)
        popover.set_has_arrow(False)
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = int(x), int(y), 1, 1
        popover.set_pointing_to(rect)
        popover.connect("closed", lambda p: GLib.idle_add(p.unparent))
        popover.popup()


class QuickRow(Gtk.ListBoxRow):
    """Connect to what was typed, when it is not a saved host."""

    def __init__(self, text):
        super().__init__(css_classes=["ssh-host", "ssh-quick"])
        self.text = text
        label = Gtk.Label(xalign=0, hexpand=True, ellipsize=Pango.EllipsizeMode.END, use_markup=True,
                          label=_("Connect to %s") % ("<b>%s</b>" % GLib.markup_escape_text(text)))
        box = Gtk.Box(spacing=10, margin_start=10, margin_end=10, margin_top=10, margin_bottom=10)
        box.append(Gtk.Image(icon_name="go-next-symbolic"))
        box.append(label)
        box.append(Gtk.Label(label="Enter ↵", css_classes=["dim-label", "caption"]))
        self.set_child(box)


class SshPanel(Gtk.Box):
    """The address book, in a panel on the right of the terminals."""

    def __init__(self, window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, css_classes=["ssh-panel"])
        self.window = window
        self.hosts = window.app.ssh_hosts

        title = Gtk.Label(label=_("SSH Servers"), xalign=0, hexpand=True, css_classes=["heading"])
        close = Gtk.Button(icon_name="window-close-symbolic", css_classes=["flat", "circular"],
                           tooltip_text=_("Close") + " (Esc)")
        close.connect("clicked", lambda *_: self.window.show_ssh_panel(False))
        top = Gtk.Box(spacing=6, margin_start=12, margin_end=6, margin_top=6)
        top.append(title)
        top.append(close)

        self.search = Gtk.SearchEntry(placeholder_text=_("Search, or type user@host"),
                                      margin_start=8, margin_end=8, margin_top=6, margin_bottom=6)
        self.search.connect("search-changed", lambda *_: self.refresh())
        self.search.connect("activate", lambda *_: self.activate_first())
        self.search.connect("stop-search", lambda *_: self.window.show_ssh_panel(False))
        # Down from the search box goes to the list
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self.on_search_key)
        self.search.add_controller(keys)

        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, css_classes=["ssh-list"])
        self.list.set_header_func(self.header_for)
        self.list.connect("row-activated", self.on_row_activated)
        self.empty = Adw.StatusPage(icon_name="network-server-symbolic", title=_("No Servers Yet"),
                                    description=_("Save your servers here and connect with one click.\n"
                                                  "Hosts in ~/.ssh/config show up here by themselves."),
                                    css_classes=["compact"], vexpand=True)
        first = Gtk.Button(label=_("Add Your First Server"), halign=Gtk.Align.CENTER,
                           css_classes=["suggested-action", "pill"])
        first.connect("clicked", lambda *_: self.edit(None))
        self.empty.set_child(first)
        self.stack = Gtk.Stack()
        self.stack.add_named(Gtk.ScrolledWindow(child=self.list, vexpand=True,
                                                hscrollbar_policy=Gtk.PolicyType.NEVER), "list")
        self.stack.add_named(self.empty, "empty")

        add = Gtk.Button(child=Adw.ButtonContent(icon_name="list-add-symbolic", label=_("Add Server")),
                         css_classes=["suggested-action"], margin_start=8, margin_end=8, margin_top=6,
                         margin_bottom=8)
        add.connect("clicked", lambda *_: self.edit(None))

        self.append(top)
        self.append(self.search)
        self.append(self.stack)
        self.append(add)
        self.hosts.connect("changed", lambda *_: self.refresh())
        escape = Gtk.EventControllerKey()
        escape.connect("key-pressed", lambda c, keyval, *_: keyval == Gdk.KEY_Escape
                       and (self.window.show_ssh_panel(False) or True))
        self.add_controller(escape)

    # -- showing -----------------------------------------------------------

    def opened(self):
        self.search.set_text("")
        self.refresh()
        self.search.grab_focus()

    def all_hosts(self):
        saved = [dict(entry, saved=entry) for entry in self.hosts.entries]
        names = {entry["name"] for entry in self.hosts.entries}
        return saved + [host for host in read_ssh_config() if host["name"] not in names]

    def refresh(self):
        while (row := self.list.get_first_child()) is not None:
            self.list.remove(row)
        text = self.search.get_text().strip()
        words = text.lower().split()
        everything = self.all_hosts()
        matching = [host for host in everything
                    if all(word in " ".join(str(host.get(k) or "") for k in
                                            ("name", "host", "user", "group", "alias")).lower()
                           for word in words)]
        if not everything and not text:
            self.stack.set_visible_child_name("empty")
            return
        self.stack.set_visible_child_name("list")
        # What was typed can always be connected to, unless it is exactly a host of the list
        if text and not any(text in (h["name"], h.get("alias"), join_address(h)) for h in matching):
            self.list.append(QuickRow(text))
        order = lambda h: (h.get("group") == _("SSH Config"), (h.get("group") or "").lower(), h["name"].lower())
        for host in sorted(matching, key=order):
            self.list.append(HostRow(self, host))

    def header_for(self, row, before):
        group = row.host.get("group") or _("Servers") if isinstance(row, HostRow) else None
        previous = (before.host.get("group") or _("Servers")) if isinstance(before, HostRow) else None
        if group is not None and group != previous:
            if group == _("SSH Config"):
                group = "~/.ssh/config"
            row.set_header(Gtk.Label(label=group.upper(), xalign=0, css_classes=["ssh-group", "caption-heading"],
                                     margin_start=12, margin_top=10, margin_bottom=2))
        else:
            row.set_header(None)

    def activate_first(self):
        row = self.list.get_row_at_index(0)
        if row is not None:
            self.on_row_activated(self.list, row)

    def on_search_key(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Down:
            row = self.list.get_row_at_index(0)
            if row is not None:
                row.grab_focus()
                return True
        return False

    def on_row_activated(self, listbox, row):
        if isinstance(row, QuickRow):
            self.window.open_ssh(row.text.split()[0], "ssh " + row.text)
            self.window.show_ssh_panel(False)
        elif isinstance(row, HostRow):
            self.connect_to(row.host)

    # -- actions -----------------------------------------------------------

    def connect_to(self, host, split=False):
        self.window.open_ssh(host["name"], command_for(host), split=split)
        self.window.show_ssh_panel(False)

    def copy_command(self, host):
        self.get_clipboard().set(command_for(host))

    def confirm_remove(self, entry):
        dialog = Adw.AlertDialog(heading=_("Remove %s?") % entry["name"],
                                 body=_("It is only removed from the address book."))
        dialog.add_response("cancel", _("_Cancel"))
        dialog.add_response("remove", _("_Remove"))
        dialog.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.connect("response", lambda d, r: self.hosts.remove(entry) if r == "remove" else None)
        dialog.present(self.window)

    def edit(self, entry, template=None):
        HostDialog(self.hosts, entry, template).present(self.window)


class HostDialog(Adw.Dialog):
    """Add a server, or edit one: an address and a name are all that is needed."""

    def __init__(self, hosts, entry, template=None):
        super().__init__(title=_("Edit Server") if entry else _("Add Server"), content_width=440)
        self.hosts, self.entry = hosts, entry
        values = dict(template or entry or {})
        if template:
            values = {key: template.get(key, "") for key in ("name", "host", "user", "port")}

        main = Adw.PreferencesGroup()
        self.address = Adw.EntryRow(title=_("Address (user@host or user@host:port)"),
                                    text=join_address(values) if values.get("host") else "")
        self.address.connect("changed", lambda *_: self.validate())
        self.address.connect("entry-activated", lambda *_: self.save())
        self.name = Adw.EntryRow(title=_("Name (optional)"), text=values.get("name") or "")
        self.name.connect("entry-activated", lambda *_: self.save())
        self.group = Adw.EntryRow(title=_("Group (optional)"), text=values.get("group") or "")
        self.group.connect("entry-activated", lambda *_: self.save())
        for row in (self.address, self.name, self.group):
            main.add(row)

        more = Adw.PreferencesGroup()
        advanced = Adw.ExpanderRow(title=_("Advanced"), subtitle=_("Key file, jump host and other ssh options"),
                                   expanded=bool(values.get("key") or values.get("options")))
        self.key = Adw.EntryRow(title=_("Key File"), text=values.get("key") or "")
        browse = Gtk.Button(icon_name="folder-open-symbolic", valign=Gtk.Align.CENTER, css_classes=["flat"],
                            tooltip_text=_("Choose a Key File"))
        browse.connect("clicked", lambda *_: self.choose_key())
        self.key.add_suffix(browse)
        self.options = Adw.EntryRow(title=_("Other ssh Options (e.g. -J jumphost)"), text=values.get("options") or "")
        advanced.add_row(self.key)
        advanced.add_row(self.options)
        more.add(advanced)
        more.set_description(_("Passwords are not stored: use a key (ssh-copy-id) or your ssh agent."))

        self.save_button = Gtk.Button(label=_("Save"), css_classes=["suggested-action"])
        self.save_button.connect("clicked", lambda *_: self.save())
        header = Adw.HeaderBar(show_end_title_buttons=False, show_start_title_buttons=False)
        cancel = Gtk.Button(label=_("Cancel"))
        cancel.connect("clicked", lambda *_: self.close())
        header.pack_start(cancel)
        header.pack_end(self.save_button)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, margin_top=12, margin_bottom=18,
                      margin_start=18, margin_end=18)
        box.append(main)
        box.append(more)
        view = Adw.ToolbarView(content=box)
        view.add_top_bar(header)
        self.set_child(view)
        self.set_focus(self.address)
        self.validate()

    def parsed(self):
        return parse_address(self.address.get_text())

    def validate(self):
        user, host, port = self.parsed()
        ok = bool(host) and " " not in host and (not port or (port.isdigit() and 0 < int(port) < 65536))
        self.save_button.set_sensitive(ok)
        return ok

    def choose_key(self):
        dialog = Gtk.FileDialog(title=_("Choose a Key File"))
        folder = os.path.expanduser("~/.ssh")
        if os.path.isdir(folder):
            dialog.set_initial_folder(Gio.File.new_for_path(folder))

        def done(dialog, result):
            try:
                path = dialog.open_finish(result).get_path()
            except GLib.Error:
                return
            home = GLib.get_home_dir()
            if path.startswith(home + os.sep):
                path = "~" + path[len(home):]
            self.key.set_text(path)

        dialog.open(self.get_root(), None, done)

    def save(self):
        if not self.validate():
            return
        user, host, port = self.parsed()
        new = {"host": host, "user": user, "port": port, "key": self.key.get_text().strip(),
               "group": self.group.get_text().strip(), "options": self.options.get_text().strip()}
        new["name"] = self.name.get_text().strip() or address_of(new)
        self.hosts.put(self.entry, new)
        self.close()
