"""Vertical tabs: a narrow rail of numbered squares on the left, in place of the tab bar.

The number is the tab's position, the one Alt+1…9 goes to. A square takes the color of its tab
(a custom color, ssh, root), is shaded while a command runs and gets a dot when its tab needs
attention. The full title is in the tooltip."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import GLib, Gtk

from velocitty import GETTEXT_DOMAIN
from velocitty.i18n import l10n

_ = l10n(GETTEXT_DOMAIN)

STYLE_CLASSES = ("running", "startup", "selected")


class TabSquare(Gtk.Button):
    def __init__(self, rail, page):
        super().__init__(css_classes=["vtab"], can_focus=False, halign=Gtk.Align.CENTER)
        self.rail, self.page = rail, page
        self.number = Gtk.Label(css_classes=["vtab-number"])
        self.dot = Gtk.Box(css_classes=["vtab-attention"], halign=Gtk.Align.END, valign=Gtk.Align.START,
                           visible=False, can_target=False)
        self.number.set_size_request(38, 38)
        overlay = Gtk.Overlay(child=self.number)
        overlay.add_overlay(self.dot)
        self.set_child(overlay)
        self.connect("clicked", lambda *_: rail.view.set_selected_page(page))
        self.handlers = [page.connect("notify::title", lambda *_: self.update()),
                         page.connect("notify::tooltip", lambda *_: self.update()),
                         page.connect("notify::needs-attention", lambda *_: self.update())]

        # Middle click closes, right click customizes, as in the tab bar
        click = Gtk.GestureClick(button=0)
        click.connect("pressed", self.on_click)
        self.add_controller(click)

    def disconnect_page(self):
        for handler in self.handlers:
            self.page.disconnect(handler)

    def update(self):
        position = self.rail.view.get_page_position(self.page)
        self.number.set_label(str(position + 1) if position >= 0 else "")
        tooltip = self.page.get_tooltip() or GLib.markup_escape_text(self.page.get_title() or "")
        if 0 <= position < 10:
            tooltip += "\n<small>Alt+%d</small>" % ((position + 1) % 10)
        self.set_tooltip_markup(tooltip)
        self.dot.set_visible(self.page.get_needs_attention())

    def on_click(self, gesture, n_press, x, y):
        button = gesture.get_current_button()
        if button == 2:
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
            self.rail.view.close_page(self.page)
        elif button == 3:
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
            child = self.page.get_child()
            if child is not None:
                self.rail.window.customize_tab(child.active)


class TabRail(Gtk.Box):
    """The squares of the tabs of a window, kept in step with the tab view."""

    def __init__(self, window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, css_classes=["vtabs"])
        self.window = window
        self.view = window.tab_view
        self.squares = []

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_top=8, margin_bottom=8)
        scroller = Gtk.ScrolledWindow(child=self.box, vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER,
                                      vscrollbar_policy=Gtk.PolicyType.EXTERNAL)
        new_tab = Gtk.Button(icon_name="xsi-tab-new-symbolic", css_classes=["vtab", "vtab-new"],
                             action_name="win.new-tab", tooltip_text=_("New Tab"), can_focus=False,
                             halign=Gtk.Align.CENTER, margin_bottom=8)
        self.append(scroller)
        self.append(new_tab)

        # The tab view keeps no reference to this model: without one here it goes, and its signals with it
        self.pages = self.view.get_pages()
        self.pages.connect("items-changed", lambda *_: GLib.idle_add(self.rebuild))
        self.pages.connect("selection-changed", lambda *_: self.window.queue_restyle())
        self.rebuild()

    def rebuild(self):
        for square in self.squares:
            square.disconnect_page()
            self.box.remove(square)
        self.squares = []
        for i in range(self.view.get_n_pages()):
            square = TabSquare(self, self.view.get_nth_page(i))
            self.box.append(square)
            self.squares.append(square)
            square.update()
        self.window.queue_restyle()
        return GLib.SOURCE_REMOVE
