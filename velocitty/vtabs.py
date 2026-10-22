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
        position = self.rail.position_of(self.page)
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

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_top=4, margin_bottom=4)
        self.scroller = Gtk.ScrolledWindow(child=self.box, vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER,
                                           vscrollbar_policy=Gtk.PolicyType.EXTERNAL)
        self.adjustment = self.scroller.get_vadjustment()
        # The adjustment changes while the rail is being laid out: showing or hiding an arrow
        # then would change the children of a box in the middle of its allocation
        self.arrows_queued = False
        self.adjustment.connect("value-changed", lambda *_: self.queue_arrows())
        self.adjustment.connect("changed", lambda *_: self.queue_arrows())

        # When the squares don't all fit, an arrow at each end says how many are hidden there
        self.up = self.arrow("xsi-go-up-symbolic", -1)
        self.down = self.arrow("xsi-go-down-symbolic", 1)
        self.append(self.up)
        self.append(self.scroller)
        self.append(self.down)

        # The tab view keeps no reference to this model: without one here it goes, and its signals with it
        self.pages = self.view.get_pages()
        self.pages.connect("items-changed", lambda *_: GLib.idle_add(self.rebuild))
        self.pages.connect("selection-changed", lambda *_: self.on_selection_changed())
        self.rebuild()

    def arrow(self, icon, direction):
        count = Gtk.Label(css_classes=["vtab-hidden-count"])
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, halign=Gtk.Align.CENTER)
        if direction < 0:
            box.append(Gtk.Image(icon_name=icon))
            box.append(count)
        else:
            box.append(count)
            box.append(Gtk.Image(icon_name=icon))
        button = Gtk.Button(child=box, css_classes=["vtab-arrow", "flat"], can_focus=False,
                            halign=Gtk.Align.CENTER, visible=False, margin_top=4, margin_bottom=4)
        button.count = count
        button.connect("clicked", lambda *_: self.scroll_by(direction))
        return button

    def position_of(self, page):
        """The page's position, or -1 when it has left the view (it is being closed or moved):
        asking the view about such a page is an error."""
        for i in range(self.view.get_n_pages()):
            if self.view.get_nth_page(i) is page:
                return i
        return -1

    def square_bounds(self, square):
        ok, bounds = square.compute_bounds(self.box)
        return (bounds.get_y(), bounds.get_y() + bounds.get_height()) if ok else None

    def queue_arrows(self):
        if not self.arrows_queued:
            self.arrows_queued = True
            GLib.idle_add(self.update_arrows)

    def update_arrows(self):
        self.arrows_queued = False
        top = self.adjustment.get_value()
        bottom = top + self.adjustment.get_page_size()
        above = below = 0
        for square in self.squares:
            bounds = self.square_bounds(square)
            if bounds is None:
                continue
            if bounds[1] <= top + 4:
                above += 1
            elif bounds[0] >= bottom - 4:
                below += 1
        for button, hidden in ((self.up, above), (self.down, below)):
            if button.get_visible() != (hidden > 0):
                button.set_visible(hidden > 0)
            if button.count.get_label() != str(hidden):
                button.count.set_label(str(hidden))
                button.set_tooltip_text(_("%d more tabs") % hidden if hidden != 1 else _("1 more tab"))
        return GLib.SOURCE_REMOVE

    def scroll_by(self, direction):
        step = max(self.adjustment.get_page_size() - 44, 44)
        self.adjustment.set_value(self.adjustment.get_value() + direction * step)

    def on_selection_changed(self):
        self.window.queue_restyle()
        GLib.idle_add(self.show_selected)

    def show_selected(self):
        """Scroll the square of the tab in front into view."""
        selected = self.view.get_selected_page()
        square = next((s for s in self.squares if s.page is selected), None)
        bounds = self.square_bounds(square) if square else None
        if bounds is not None:
            top = self.adjustment.get_value()
            bottom = top + self.adjustment.get_page_size()
            if bounds[0] < top:
                self.adjustment.set_value(bounds[0] - 4)
            elif bounds[1] > bottom:
                self.adjustment.set_value(bounds[1] - self.adjustment.get_page_size() + 4)
        self.queue_arrows()
        return GLib.SOURCE_REMOVE

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
        GLib.idle_add(self.show_selected)
        return GLib.SOURCE_REMOVE
