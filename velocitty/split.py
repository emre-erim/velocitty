import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, GLib, Gtk

INACTIVE_CLASS = "split-inactive"


class SplitTab(Adw.Bin):
    """What a page of the tab view holds: one terminal, or terminals split side by side
    or one above the other, to any depth. The terminals are the leaves of a tree of
    Gtk.Paned. One of them is active: the one that had the focus last. The tab bar, the
    headerbar and the shortcuts work on the active one."""

    def __init__(self, pane):
        super().__init__()
        self.active = pane
        self.set_child(pane)
        self.adopt(pane)

    # -- tree --------------------------------------------------------------

    def panes(self):
        """The terminals, left to right and top to bottom."""
        found = []

        def visit(widget):
            if isinstance(widget, Gtk.Paned):
                visit(widget.get_start_child())
                visit(widget.get_end_child())
            elif widget is not None:
                found.append(widget)

        visit(self.get_child())
        return found

    def is_split(self):
        return isinstance(self.get_child(), Gtk.Paned)

    def replace(self, old, new):
        """Put new where old is in the tree. old is taken out."""
        parent = old.get_parent()
        if parent is self:
            self.set_child(None)
            self.set_child(new)
        elif isinstance(parent, Gtk.Paned):
            if parent.get_start_child() is old:
                parent.set_start_child(None)
                parent.set_start_child(new)
            else:
                parent.set_end_child(None)
                parent.set_end_child(new)

    def adopt(self, pane):
        focus = Gtk.EventControllerFocus()
        focus.connect("enter", lambda *_: self.on_pane_focused(pane))
        pane.add_controller(focus)

    def split(self, pane, new_pane, orientation):
        """Split pane in two: it stays first, new_pane goes to its right or below it."""
        horizontal = orientation == Gtk.Orientation.HORIZONTAL
        size = pane.get_width() if horizontal else pane.get_height()
        paned = Gtk.Paned(orientation=orientation, wide_handle=False,
                          resize_start_child=True, resize_end_child=True,
                          shrink_start_child=False, shrink_end_child=False)
        self.replace(pane, paned)
        paned.set_start_child(pane)
        paned.set_end_child(new_pane)
        if size > 0:
            paned.set_position(size // 2)
        self.adopt(new_pane)
        self.set_active(new_pane)

    def remove(self, pane):
        """Take a terminal out: its neighbour takes the room. Returns the terminal that
        becomes active, or None when it was the last one."""
        parent = pane.get_parent()
        if not isinstance(parent, Gtk.Paned):
            return None
        sibling = parent.get_end_child() if parent.get_start_child() is pane else parent.get_start_child()
        # Move the focus out before taking the pane out, GtkPaned keeps track of it
        if pane.get_focus_child() is not None or pane.has_focus():
            SplitTab.leaves(sibling)[0].terminal.grab_focus()
        parent.set_start_child(None)
        parent.set_end_child(None)
        self.replace(parent, sibling)
        if self.active is pane or self.active not in self.panes():
            self.set_active(SplitTab.leaves(sibling)[0])
        else:
            self.set_active(self.active)
        return self.active

    @staticmethod
    def leaves(widget):
        if isinstance(widget, Gtk.Paned):
            return SplitTab.leaves(widget.get_start_child()) + SplitTab.leaves(widget.get_end_child())
        return [widget] if widget is not None else []

    def equalize(self):
        """Give the panes of each split the same room."""
        def visit(widget):
            if not isinstance(widget, Gtk.Paned):
                return
            horizontal = widget.get_orientation() == Gtk.Orientation.HORIZONTAL
            size = widget.get_width() if horizontal else widget.get_height()
            if size > 0:
                widget.set_position(size // 2)
            visit(widget.get_start_child())
            visit(widget.get_end_child())
        visit(self.get_child())

    # -- active pane -------------------------------------------------------

    def on_pane_focused(self, pane):
        if pane.get_parent() is None or pane not in self.panes():
            return
        if pane is not self.active:
            self.set_active(pane)

    def set_active(self, pane):
        self.active = pane
        panes = self.panes()
        split = len(panes) > 1
        for other in panes:
            if split and other is not pane:
                other.add_css_class(INACTIVE_CLASS)
            else:
                other.remove_css_class(INACTIVE_CLASS)
        window = getattr(pane, "window", None)
        if window is not None:
            window.active_pane_changed(self, pane)

    def neighbor(self, pane, direction):
        """The terminal next to pane on that side ("left", "right", "up", "down"), or None."""
        ok, here = pane.compute_bounds(self)
        if not ok:
            return None
        x0, y0 = here.get_x(), here.get_y()
        x1, y1 = x0 + here.get_width(), y0 + here.get_height()
        best = None
        for other in self.panes():
            if other is pane:
                continue
            ok, there = other.compute_bounds(self)
            if not ok:
                continue
            ox0, oy0 = there.get_x(), there.get_y()
            ox1, oy1 = ox0 + there.get_width(), oy0 + there.get_height()
            if direction == "left" and ox1 <= x0 + 1:
                gap, overlap = x0 - ox1, min(y1, oy1) - max(y0, oy0)
            elif direction == "right" and ox0 >= x1 - 1:
                gap, overlap = ox0 - x1, min(y1, oy1) - max(y0, oy0)
            elif direction == "up" and oy1 <= y0 + 1:
                gap, overlap = y0 - oy1, min(x1, ox1) - max(x0, ox0)
            elif direction == "down" and oy0 >= y1 - 1:
                gap, overlap = oy0 - y1, min(x1, ox1) - max(x0, ox0)
            else:
                continue
            if overlap <= 0:
                continue
            key = (gap, -overlap)
            if best is None or key < best[0]:
                best = (key, other)
        return best[1] if best else None

    def cycle(self, pane, step):
        """The next (+1) or previous (-1) terminal, in order."""
        panes = self.panes()
        if len(panes) < 2 or pane not in panes:
            return None
        return panes[(panes.index(pane) + step) % len(panes)]


def split_of(widget):
    """The SplitTab a terminal is in, or None."""
    while widget is not None and not isinstance(widget, SplitTab):
        widget = widget.get_parent()
    return widget


def focus_later(pane):
    GLib.idle_add(lambda: pane.terminal.grab_focus() and False)
