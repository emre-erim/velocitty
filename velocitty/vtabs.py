"""Vertical tabs: the tabs listed in a sidebar, in place of the tab bar."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, GObject, Gtk, Pango

from velocitty import GETTEXT_DOMAIN
from velocitty.i18n import l10n

_ = l10n(GETTEXT_DOMAIN)

SIDEBAR_WIDTH = 220


class TabRow(Gtk.ListBoxRow):
    def __init__(self, sidebar, page):
        super().__init__(css_classes=["vtab"])
        self.page = page
        self.title = Gtk.Label(xalign=0, hexpand=True, ellipsize=Pango.EllipsizeMode.MIDDLE)
        page.bind_property("title", self.title, "label", GObject.BindingFlags.SYNC_CREATE)
        page.bind_property("tooltip", self, "tooltip-markup", GObject.BindingFlags.SYNC_CREATE)
        self.dot = Gtk.Box(css_classes=["vtab-attention"], valign=Gtk.Align.CENTER)
        page.bind_property("needs-attention", self.dot, "visible", GObject.BindingFlags.SYNC_CREATE)
        close = Gtk.Button(icon_name="xsi-window-close-symbolic", css_classes=["flat", "circular", "vtab-close"],
                           valign=Gtk.Align.CENTER, tooltip_text=_("Close Tab"))
        close.connect("clicked", lambda *_: sidebar.view.close_page(page))
        box = Gtk.Box(spacing=6, margin_start=10, margin_end=4, margin_top=2, margin_bottom=2)
        box.append(self.title)
        box.append(self.dot)
        box.append(close)
        self.set_child(box)

        # Middle click closes, right click edits the tab, as in the tab bar
        click = Gtk.GestureClick(button=0)
        click.connect("pressed", self.on_click, sidebar)
        self.add_controller(click)

    def on_click(self, gesture, n_press, x, y, sidebar):
        button = gesture.get_current_button()
        if button == 2:
            sidebar.view.close_page(self.page)
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        elif button == 3:
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
            child = self.page.get_child()
            if child is not None:
                sidebar.window.customize_tab(child.active)


class TabSidebar(Gtk.Box):
    """The list of the tabs of a window, one row each, kept in step with the tab view."""

    def __init__(self, window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, css_classes=["vtabs"],
                         width_request=140)
        self.window = window
        self.view = window.tab_view
        self.syncing = False

        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE, css_classes=["vtabs-list"])
        self.list.set_can_focus(False)
        self.pages = self.view.get_pages()
        self.list.bind_model(self.pages, lambda page: TabRow(self, page))
        self.list.connect("row-selected", self.on_row_selected)
        self.pages.connect("selection-changed", lambda *_: GLib.idle_add(self.sync_selection))
        self.pages.connect("items-changed", lambda *_: GLib.idle_add(self.after_change))

        scroller = Gtk.ScrolledWindow(child=self.list, vexpand=True,
                                      hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.append(scroller)

    def rows(self):
        row = self.list.get_first_child()
        while row is not None:
            if isinstance(row, TabRow):
                yield row
            row = row.get_next_sibling()

    def after_change(self):
        self.sync_selection()
        self.window.queue_restyle()
        return GLib.SOURCE_REMOVE

    def sync_selection(self):
        selected = self.view.get_selected_page()
        index = self.view.get_page_position(selected) if selected is not None else -1
        row = self.list.get_row_at_index(index) if index >= 0 else None
        if row is not None and self.list.get_selected_row() is not row:
            self.syncing = True
            self.list.select_row(row)
            self.syncing = False
        return GLib.SOURCE_REMOVE

    def on_row_selected(self, listbox, row):
        if self.syncing or row is None:
            return
        if self.view.get_selected_page() is not row.page:
            self.view.set_selected_page(row.page)
        GLib.idle_add(self.window.focus_terminal)
