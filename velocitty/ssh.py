"""The SSH address book: hosts saved here, and the hosts of ~/.ssh/config, to open in a new tab."""

import glob
import json
import os
import shlex

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, GObject, Gtk

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

class SshPage(Adw.NavigationPage):
    """The address book: search, connect, add, edit and remove hosts."""

    def __init__(self, window):
        super().__init__(title=_("SSH Hosts"), tag="ssh-hosts")
        self.window = window
        self.hosts = window.app.ssh_hosts
        self.matching = []   # the hosts that match the search, in order

        self.search = Gtk.SearchEntry(placeholder_text=_("Search, or type user@host to connect"),
                                      hexpand=True)
        self.search.connect("search-changed", lambda *_: self.refresh())
        self.search.connect("activate", self.on_activate)
        self.search.connect("stop-search", lambda *_: self.window.nav.pop())

        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        clamp = Adw.Clamp(maximum_size=720, child=self.content, margin_top=12, margin_bottom=24,
                          margin_start=12, margin_end=12, valign=Gtk.Align.START)
        scroller = Gtk.ScrolledWindow(child=clamp, vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)

        header = Adw.HeaderBar(title_widget=Adw.Clamp(maximum_size=480, child=self.search))
        add = Gtk.Button(icon_name="list-add-symbolic", tooltip_text=_("Add Host"))
        add.connect("clicked", lambda *_: self.edit(None))
        header.pack_end(add)

        view = Adw.ToolbarView(content=scroller, css_classes=["custom-tabs"])
        view.add_top_bar(header)
        self.set_child(view)
        self.hosts.connect("changed", lambda *_: self.refresh())
        self.connect("shown", lambda *_: self.on_shown())

    def on_shown(self):
        self.search.set_text("")
        self.refresh()
        self.search.grab_focus()

    def all_hosts(self):
        saved = [dict(entry, saved=entry) for entry in self.hosts.entries]
        names = {entry["name"] for entry in self.hosts.entries}
        return saved + [host for host in read_ssh_config() if host["name"] not in names]

    def matches(self, host, words):
        text = " ".join(str(host.get(key) or "") for key in ("name", "host", "user", "group", "alias")).lower()
        return all(word in text for word in words)

    def refresh(self):
        while (child := self.content.get_first_child()) is not None:
            self.content.remove(child)
        words = self.search.get_text().lower().split()
        self.matching = [host for host in self.all_hosts() if self.matches(host, words)]

        groups = {}
        for host in self.matching:
            groups.setdefault(host.get("group") or _("Hosts"), []).append(host)
        for name in sorted(groups, key=lambda g: (g == _("SSH Config"), g.lower())):
            group = Adw.PreferencesGroup(title=GLib.markup_escape_text(name))
            for host in sorted(groups[name], key=lambda h: h["name"].lower()):
                group.add(self.build_row(host))
            self.content.append(group)

        text = self.search.get_text().strip()
        if not self.matching:
            if text:
                hint = _("Press Enter to connect to %s") % text
            else:
                hint = _("No hosts yet. Add one with +, or put them in ~/.ssh/config.")
            self.content.append(Adw.StatusPage(icon_name="network-server-symbolic", title=_("SSH Hosts"),
                                               description=GLib.markup_escape_text(hint)))

    def build_row(self, host):
        subtitle = address_of(host)
        if host.get("alias") and host.get("host") != host.get("alias"):
            subtitle = "%s → %s" % (host["alias"], subtitle)
        row = Adw.ActionRow(title=GLib.markup_escape_text(host["name"]),
                            subtitle=GLib.markup_escape_text(subtitle), activatable=True)
        row.add_prefix(Gtk.Image(icon_name="network-server-symbolic"))
        row.connect("activated", lambda *_: self.connect_to(host))
        if host.get("saved") is not None:
            edit = Gtk.Button(icon_name="document-edit-symbolic", valign=Gtk.Align.CENTER,
                              css_classes=["flat", "circular"], tooltip_text=_("Edit"))
            edit.connect("clicked", lambda *_: self.edit(host["saved"]))
            row.add_suffix(edit)
            remove = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER,
                                css_classes=["flat", "circular"], tooltip_text=_("Remove"))
            remove.connect("clicked", lambda *_: self.confirm_remove(host["saved"]))
            row.add_suffix(remove)
        else:
            copy = Gtk.Button(icon_name="list-add-symbolic", valign=Gtk.Align.CENTER,
                              css_classes=["flat", "circular"], tooltip_text=_("Save to the Address Book"))
            copy.connect("clicked", lambda *_: self.edit(None, template=host))
            row.add_suffix(copy)
        return row

    def on_activate(self, entry):
        text = entry.get_text().strip()
        if len(self.matching) == 1:
            self.connect_to(self.matching[0])
        elif not self.matching and text:
            # Quick connect: anything ssh understands, like user@host or host -p 2222
            self.window.open_ssh(_("SSH") + " " + text.split()[0], "ssh " + text)

    def connect_to(self, host):
        self.window.open_ssh(host["name"], command_for(host))

    def confirm_remove(self, entry):
        dialog = Adw.AlertDialog(heading=_("Remove %s?") % entry["name"],
                                 body=_("It is removed from the address book only."))
        dialog.add_response("cancel", _("_Cancel"))
        dialog.add_response("remove", _("_Remove"))
        dialog.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.connect("response", lambda d, r: self.hosts.remove(entry) if r == "remove" else None)
        dialog.present(self.window)

    def edit(self, entry, template=None):
        HostDialog(self.hosts, entry, template).present(self.window)


class HostDialog(Adw.Dialog):
    """Add a host, or edit one."""

    def __init__(self, hosts, entry, template=None):
        super().__init__(title=_("Edit Host") if entry else _("Add Host"), content_width=460)
        self.hosts, self.entry = hosts, entry
        values = dict(entry or {})
        if template:
            values = {"name": template.get("name", ""), "host": template.get("host", ""),
                      "user": template.get("user", ""), "port": template.get("port", ""),
                      "group": ""}

        self.rows = {}
        group = Adw.PreferencesGroup()
        for key, title in (("name", _("Name")), ("host", _("Host")), ("user", _("User")),
                           ("port", _("Port")), ("group", _("Group"))):
            row = Adw.EntryRow(title=title, text=str(values.get(key) or ""))
            row.connect("changed", lambda *_: self.validate())
            self.rows[key] = row
            group.add(row)
        advanced = Adw.PreferencesGroup(title=_("Advanced"))
        key_row = Adw.EntryRow(title=_("Key File"), text=values.get("key") or "")
        browse = Gtk.Button(icon_name="folder-open-symbolic", valign=Gtk.Align.CENTER,
                            css_classes=["flat"], tooltip_text=_("Choose a Key File"))
        browse.connect("clicked", lambda *_: self.choose_key())
        key_row.add_suffix(browse)
        self.rows["key"] = key_row
        options = Adw.EntryRow(title=_("Other ssh Options (e.g. -J jumphost)"), text=values.get("options") or "")
        self.rows["options"] = options
        advanced.add(key_row)
        advanced.add(options)
        advanced.set_description(_("Passwords are not stored: use a key (ssh-copy-id) or your ssh agent."))

        self.save_button = Gtk.Button(label=_("Save"), css_classes=["suggested-action"])
        self.save_button.connect("clicked", lambda *_: self.save())
        header = Adw.HeaderBar(show_end_title_buttons=False, show_start_title_buttons=False)
        cancel = Gtk.Button(label=_("Cancel"))
        cancel.connect("clicked", lambda *_: self.close())
        header.pack_start(cancel)
        header.pack_end(self.save_button)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, margin_top=12, margin_bottom=18,
                      margin_start=18, margin_end=18)
        box.append(group)
        box.append(advanced)
        view = Adw.ToolbarView(content=box)
        view.add_top_bar(header)
        self.set_child(view)
        self.set_default_widget(self.save_button)
        self.validate()

    def value(self, key):
        return self.rows[key].get_text().strip()

    def validate(self):
        port = self.value("port")
        ok = bool(self.value("host")) and (not port or (port.isdigit() and 0 < int(port) < 65536))
        self.save_button.set_sensitive(ok)
        return ok

    def choose_key(self):
        dialog = Gtk.FileDialog(title=_("Choose a Key File"))
        folder = os.path.expanduser("~/.ssh")
        if os.path.isdir(folder):
            from gi.repository import Gio
            dialog.set_initial_folder(Gio.File.new_for_path(folder))

        def done(dialog, result):
            try:
                path = dialog.open_finish(result).get_path()
            except GLib.Error:
                return
            home = GLib.get_home_dir()
            if path.startswith(home + os.sep):
                path = "~" + path[len(home):]
            self.rows["key"].set_text(path)

        dialog.open(self.get_root(), None, done)

    def save(self):
        if not self.validate():
            return
        new = {key: self.value(key) for key in FIELDS}
        new["name"] = new["name"] or address_of(new)
        self.hosts.put(self.entry, new)
        self.close()
